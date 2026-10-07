import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import Assistant from "../src/pages/portal/Assistant.jsx";
import { StoreProvider } from "../src/data/store.jsx";
import { RequireRole } from "../src/components/ui.jsx";
import { CHAT_MESSAGES, ChatError, createChatApi } from "../src/api/chat.js";

const future = { v7_startTransition: true, v7_relativeSplatPath: true };
const QUOTE = { status: "proposed", currency: "PEN", total: "260.00", lines: [{ label: "Instalación de SSD", amount: "80.00" }, { label: "SSD de 480 GB", amount: "180.00" }] };

function Acceso() {
  const { state } = useLocation();
  return <h1>Acceso{state?.from ? ` · vuelve a ${state.from}` : ""}</h1>;
}

function renderChat(api) {
  sessionStorage.setItem("techfix.session", JSON.stringify({ role: "client", name: "Ana Torres", email: "ana@demo.pe" }));
  return render(
    <MemoryRouter future={future} initialEntries={["/portal/asistente"]}>
      <StoreProvider>
        <Routes>
          <Route path="/portal/asistente" element={<RequireRole role="client"><Assistant api={api} /></RequireRole>} />
          <Route path="/" element={<h1>Landing</h1>} />
          <Route path="/portal/acceso" element={<Acceso />} />
        </Routes>
      </StoreProvider>
    </MemoryRouter>
  );
}

async function write(user, text) {
  await user.type(screen.getByLabelText("Mensaje"), `${text}{Enter}`);
}

describe("cliente del chat", () => {
  it("envía POST /api/chat con cookie y sin datos del cliente", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ conversation_id: "c1", reply: "Hola" }) });
    const api = createChatApi({ baseUrl: "http://chat.local/", fetchImpl });
    await api.sendMessage({ message: "Mi laptop no enciende" });

    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://chat.local/api/chat");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ conversation_id: null, message: "Mi laptop no enciende", action: null, pattern: "hierarchical" });
  });

  it.each([[401, "session_required"], [403, "customer_only"], [404, "not_found"], [429, "rate_limited"], [503, "unavailable"]])(
    "traduce %i a %s", async (status, code) => {
      const api = createChatApi({ baseUrl: "http://chat.local", fetchImpl: vi.fn().mockResolvedValue({ ok: false, status, json: async () => ({}) }) });
      await expect(api.sendMessage({ message: "x" })).rejects.toMatchObject({ code });
    });

  it("sin VITE_CHAT_URL queda en modo demostración", () => {
    expect(createChatApi().mode).toBe("mock");
  });
});

describe("asistente conectado", () => {
  it("saluda con la sesión, muestra presupuesto y ticket y acepta", async () => {
    const api = {
      mode: "api",
      sendMessage: vi.fn()
        .mockResolvedValueOnce({ conversation_id: "c1", reply: "Preparé el presupuesto.", quote: QUOTE, ticket: { code: "TCK-4F2A1C", status: "QUOTED" } })
        .mockResolvedValueOnce({ conversation_id: "c1", reply: "Guardé el ticket y presupuesto.", quote: { ...QUOTE, status: "saved" }, ticket: { code: "TCK-4F2A1C", status: "QUOTED" } }),
    };
    const user = userEvent.setup();
    renderChat(api);

    expect(screen.getByText(/Hola, Ana/)).toBeInTheDocument();
    await write(user, "Mi laptop no detecta el disco");
    expect(api.sendMessage).toHaveBeenCalledWith({ conversationId: null, pattern: "hierarchical", message: "Mi laptop no detecta el disco" });
    expect(await screen.findByText("Preparé el presupuesto.")).toBeInTheDocument();
    expect(screen.getByText("S/. 260.00")).toBeInTheDocument();
    expect(screen.getAllByText("Estado: Presupuesto enviado").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /confirmar y guardar/i }));
    expect(api.sendMessage).toHaveBeenLastCalledWith({ conversationId: "c1", pattern: "hierarchical", action: "accept_quote" });
    expect((await screen.findAllByText("Estado: Presupuesto enviado")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/pendiente de aceptación/).length).toBeGreaterThan(0);
  });

  it("permite elegir el patrón antes de empezar y bloquea cambios durante la conversación", async () => {
    const api = {
      mode: "api",
      sendMessage: vi.fn().mockResolvedValue({ conversation_id: "c1", reply: "Respuesta del patrón." }),
    };
    const user = userEvent.setup();
    renderChat(api);

    const selector = screen.getByLabelText("Patrón de agentes");
    await user.selectOptions(selector, "decentralized");
    expect(screen.getByRole("status")).toHaveTextContent("no guarda tickets ni presupuestos");
    await write(user, "Mi laptop no enciende desde ayer");
    expect(api.sendMessage).toHaveBeenCalledWith({
      conversationId: null,
      pattern: "decentralized",
      message: "Mi laptop no enciende desde ayer",
    });
    expect(selector).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /nueva conversación/i }));
    expect(selector).toBeEnabled();
    await user.selectOptions(selector, "orchestrator");
    expect(selector).toHaveValue("orchestrator");
  });

  it("si la sesión terminó lleva al acceso", async () => {
    const api = { mode: "api", sendMessage: vi.fn().mockRejectedValue(new ChatError(CHAT_MESSAGES.session, { status: 401, code: "session_required" })) };
    const user = userEvent.setup();
    renderChat(api);
    await write(user, "Mi laptop no enciende desde ayer");
    expect(await screen.findByRole("heading", { name: "Acceso · vuelve a /portal/asistente" })).toBeInTheDocument();
    expect(sessionStorage.getItem("techfix.session")).toBeNull();
  });

  it("ante un error temporal permite reintentar", async () => {
    const api = {
      mode: "api",
      sendMessage: vi.fn()
        .mockRejectedValueOnce(new ChatError(CHAT_MESSAGES.unavailable, { status: 503, code: "unavailable" }))
        .mockResolvedValueOnce({ conversation_id: "c1", reply: "Ya estoy disponible." }),
    };
    const user = userEvent.setup();
    renderChat(api);
    await write(user, "Mi laptop no enciende desde ayer");
    expect(await screen.findByRole("alert")).toHaveTextContent(CHAT_MESSAGES.unavailable);
    await user.click(screen.getByRole("button", { name: /reintentar/i }));
    expect(await screen.findByText("Ya estoy disponible.")).toBeInTheDocument();
    expect(api.sendMessage).toHaveBeenCalledTimes(2);
  });

  it("un técnico ve el aviso de que el chat es para clientes", async () => {
    const api = { mode: "api", sendMessage: vi.fn().mockRejectedValue(new ChatError(CHAT_MESSAGES.customerOnly, { status: 403, code: "customer_only" })) };
    const user = userEvent.setup();
    renderChat(api);
    await write(user, "Prueba del chat del portal");
    expect(await screen.findByRole("alert")).toHaveTextContent(CHAT_MESSAGES.customerOnly);
  });
});

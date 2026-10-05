import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Assistant from "../src/pages/portal/Assistant.jsx";
import { StoreProvider } from "../src/data/store.jsx";
import { CHAT_MESSAGES, ChatError, createChatApi } from "../src/api/chat.js";

const future = { v7_startTransition: true, v7_relativeSplatPath: true };
const QUOTE = { status: "proposed", currency: "PEN", total: "260.00", lines: [{ label: "Instalación de SSD", amount: "80.00" }, { label: "SSD de 480 GB", amount: "180.00" }] };

function renderChat(api) {
  sessionStorage.setItem("techfix.session", JSON.stringify({ role: "client", name: "Ana Torres", email: "ana@demo.pe" }));
  return render(
    <MemoryRouter future={future} initialEntries={["/portal/asistente"]}>
      <StoreProvider>
        <Routes>
          <Route path="/portal/asistente" element={<Assistant api={api} />} />
          <Route path="/portal/acceso" element={<h1>Acceso</h1>} />
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
    expect(JSON.parse(init.body)).toEqual({ conversation_id: null, message: "Mi laptop no enciende", action: null });
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
        .mockResolvedValueOnce({ conversation_id: "c1", reply: "Listo, registré tu aprobación.", quote: { ...QUOTE, status: "confirmed" }, ticket: { code: "TCK-4F2A1C", status: "IN_REPAIR" } }),
    };
    const user = userEvent.setup();
    renderChat(api);

    expect(screen.getByText(/Hola, Ana/)).toBeInTheDocument();
    await write(user, "Mi laptop no detecta el disco");
    expect(api.sendMessage).toHaveBeenCalledWith({ conversationId: null, message: "Mi laptop no detecta el disco" });
    expect(await screen.findByText("Preparé el presupuesto.")).toBeInTheDocument();
    expect(screen.getByText("S/. 260.00")).toBeInTheDocument();
    expect(screen.getByText("Estado: Presupuesto enviado")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /aceptar presupuesto/i }));
    expect(api.sendMessage).toHaveBeenLastCalledWith({ conversationId: "c1", action: "accept_quote" });
    expect(await screen.findByText("Estado: En reparación")).toBeInTheDocument();
    expect(screen.getAllByText(/Presupuesto aceptado/).length).toBeGreaterThan(0);
  });

  it("si la sesión terminó lleva al acceso", async () => {
    const api = { mode: "api", sendMessage: vi.fn().mockRejectedValue(new ChatError(CHAT_MESSAGES.session, { status: 401, code: "session_required" })) };
    const user = userEvent.setup();
    renderChat(api);
    await write(user, "Mi laptop no enciende desde ayer");
    expect(await screen.findByRole("heading", { name: "Acceso" })).toBeInTheDocument();
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

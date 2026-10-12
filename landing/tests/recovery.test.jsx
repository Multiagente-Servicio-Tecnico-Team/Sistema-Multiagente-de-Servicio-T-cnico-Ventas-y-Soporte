import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Recover from "../src/pages/portal/Recover.jsx";
import Reset from "../src/pages/portal/Reset.jsx";
import { StoreProvider } from "../src/data/store.jsx";
import { ApiError, createAuthApi, MESSAGES } from "../src/api/auth.js";

const future = { v7_startTransition: true, v7_relativeSplatPath: true };

function renderAt(path, element, routePath) {
  return render(
    <MemoryRouter future={future} initialEntries={[path]}>
      <StoreProvider>
        <Routes>
          <Route path={routePath} element={element} />
          <Route path="/portal/acceso" element={<h1>Acceso</h1>} />
          <Route path="/portal/recuperar" element={<h1>Recuperar</h1>} />
        </Routes>
      </StoreProvider>
    </MemoryRouter>
  );
}

describe("recuperar contraseña", () => {
  it("valida el correo y no llama a la API si es inválido", async () => {
    const api = { mode: "api", requestPasswordReset: vi.fn() };
    const user = userEvent.setup();
    renderAt("/portal/recuperar", <Recover api={api} />, "/portal/recuperar");

    await user.type(screen.getByLabelText("Correo Electrónico Registrado"), "no-es-correo");
    await user.click(screen.getByRole("button", { name: /enviar enlace/i }));

    expect(screen.getByText("Ingresa un correo electrónico válido.")).toBeInTheDocument();
    expect(api.requestPasswordReset).not.toHaveBeenCalled();
  });

  it("muestra la confirmación sin revelar si el correo existe", async () => {
    const api = { mode: "api", requestPasswordReset: vi.fn().mockResolvedValue({ ok: true }) };
    const user = userEvent.setup();
    renderAt("/portal/recuperar", <Recover api={api} />, "/portal/recuperar");

    await user.type(screen.getByLabelText("Correo Electrónico Registrado"), "ana@demo.pe");
    await user.click(screen.getByRole("button", { name: /enviar enlace/i }));

    expect(await screen.findByRole("heading", { name: "Revisa tu correo" })).toBeInTheDocument();
    expect(screen.getByText(/Si/)).toHaveTextContent("está registrado");
    expect(api.requestPasswordReset).toHaveBeenCalledWith({ email: "ana@demo.pe" });
    expect(screen.queryByText("Abrir enlace de prueba")).not.toBeInTheDocument();
  });
});

describe("restablecer contraseña", () => {
  it("sin token muestra el estado de enlace inválido", () => {
    renderAt("/portal/restablecer", <Reset api={{ mode: "api", resetPassword: vi.fn() }} />, "/portal/restablecer");
    expect(screen.getByRole("heading", { name: "Enlace no válido" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /solicitar un nuevo enlace/i })).toHaveAttribute("href", "/portal/recuperar");
  });

  it("exige una contraseña segura y que coincida", async () => {
    const api = { mode: "api", resetPassword: vi.fn() };
    const user = userEvent.setup();
    renderAt("/portal/restablecer?token=abc", <Reset api={api} />, "/portal/restablecer");

    await user.type(screen.getByLabelText("Nueva Contraseña"), "debil");
    await user.type(screen.getByLabelText("Confirmar Contraseña"), "otra");
    await user.click(screen.getByRole("button", { name: /guardar nueva contraseña/i }));

    expect(screen.getByText("La contraseña no cumple todos los requisitos.")).toBeInTheDocument();
    expect(screen.getByText("Las contraseñas no coinciden.")).toBeInTheDocument();
    expect(api.resetPassword).not.toHaveBeenCalled();
  });

  it("envía token y contraseña y confirma el cambio", async () => {
    const api = { mode: "api", resetPassword: vi.fn().mockResolvedValue({ ok: true }) };
    const user = userEvent.setup();
    renderAt("/portal/restablecer?token=abc123", <Reset api={api} />, "/portal/restablecer");

    await user.type(screen.getByLabelText("Nueva Contraseña"), "Nueva#Clave2026");
    await user.type(screen.getByLabelText("Confirmar Contraseña"), "Nueva#Clave2026");
    await user.click(screen.getByRole("button", { name: /guardar nueva contraseña/i }));

    expect(await screen.findByRole("heading", { name: "Contraseña actualizada" })).toBeInTheDocument();
    expect(api.resetPassword).toHaveBeenCalledWith({ token: "abc123", password: "Nueva#Clave2026" });
  });

  it("si el token expiró ofrece pedir un enlace nuevo", async () => {
    const api = { mode: "api", resetPassword: vi.fn().mockRejectedValue(new ApiError(MESSAGES.invalidToken, { status: 410, code: "invalid_token" })) };
    const user = userEvent.setup();
    renderAt("/portal/restablecer?token=viejo", <Reset api={api} />, "/portal/restablecer");

    await user.type(screen.getByLabelText("Nueva Contraseña"), "Nueva#Clave2026");
    await user.type(screen.getByLabelText("Confirmar Contraseña"), "Nueva#Clave2026");
    await user.click(screen.getByRole("button", { name: /guardar nueva contraseña/i }));

    expect(await screen.findByRole("heading", { name: "Enlace no válido" })).toBeInTheDocument();
  });
});

describe("contrato POST /restablecer", () => {
  it("envía token y contraseña y traduce 410 a enlace inválido", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 410, json: async () => ({}) });
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });

    await expect(api.resetPassword({ token: "t1", password: "Nueva#Clave2026" })).rejects.toMatchObject({ code: "invalid_token", message: MESSAGES.invalidToken });
    expect(fetchImpl.mock.calls[0][0]).toBe("http://api.local/restablecer");
    expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toEqual({ token: "t1", password: "Nueva#Clave2026" });
  });
});

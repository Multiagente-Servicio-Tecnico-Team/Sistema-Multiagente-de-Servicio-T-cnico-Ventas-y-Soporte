import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import App from "../src/App.jsx";
import { LoginForm } from "../src/pages/portal/Login.jsx";
import { StoreProvider } from "../src/data/store.jsx";
import { ApiError, MESSAGES } from "../src/api/auth.js";

function renderLogin(api, initialEntries = ["/portal/acceso"]) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={initialEntries}>
      <StoreProvider>
        <Routes>
          <Route
            path="/portal/acceso"
            element={<LoginForm role="client" badge="Portal" title="Acceder" subtitle="" defaultTo="/portal/tickets" footer={null} api={api} />}
          />
          <Route path="/portal/tickets" element={<h1>Mis Tickets</h1>} />
        </Routes>
      </StoreProvider>
    </MemoryRouter>
  );
}

describe("inicio de sesión", () => {
  it("valida el correo antes de llamar a la API", async () => {
    const api = { mode: "api", login: vi.fn() };
    const user = userEvent.setup();
    renderLogin(api);

    await user.type(screen.getByLabelText("Correo electrónico"), "correo-invalido");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(screen.getByText("Ingresa un correo electrónico válido.")).toBeInTheDocument();
    expect(screen.getByText("Ingresa tu contraseña.")).toBeInTheDocument();
    expect(api.login).not.toHaveBeenCalled();
  });

  it("inicia sesión, redirige y guarda solo datos públicos", async () => {
    const api = { mode: "api", login: vi.fn().mockResolvedValue({ nombre: "Ana Torres", email: "ana@demo.pe" }) };
    const user = userEvent.setup();
    renderLogin(api);

    await user.type(screen.getByLabelText("Correo electrónico"), "ana@demo.pe");
    await user.type(screen.getByLabelText("Contraseña"), "Secreta#2026");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByRole("heading", { name: "Mis Tickets" })).toBeInTheDocument();
    expect(api.login).toHaveBeenCalledWith({ email: "ana@demo.pe", password: "Secreta#2026" });
    expect(sessionStorage.getItem("techfix.session")).not.toContain("Secreta");
  });

  it("muestra el error de credenciales y permite reintentar", async () => {
    const api = { mode: "api", login: vi.fn().mockRejectedValue(new ApiError(MESSAGES.invalidCredentials, { status: 401 })) };
    const user = userEvent.setup();
    renderLogin(api);

    await user.type(screen.getByLabelText("Correo electrónico"), "ana@demo.pe");
    await user.type(screen.getByLabelText("Contraseña"), "mala");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(MESSAGES.invalidCredentials);
    expect(screen.getByRole("button", { name: /iniciar sesión/i })).toBeEnabled();
  });

  it("vuelve a la página protegida solicitada después de iniciar sesión", async () => {
    const api = { mode: "api", login: vi.fn().mockResolvedValue({ nombre: "Ana", email: "ana@demo.pe" }) };
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={[{ pathname: "/portal/acceso", state: { from: "/portal/asistente" } }]}>
        <StoreProvider>
          <Routes>
            <Route path="/portal/acceso" element={<LoginForm role="client" badge="" title="" subtitle="" defaultTo="/portal/tickets" footer={null} api={api} />} />
            <Route path="/portal/asistente" element={<h1>Asistente</h1>} />
          </Routes>
        </StoreProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText("Correo electrónico"), "ana@demo.pe");
    await user.type(screen.getByLabelText("Contraseña"), "Secreta#2026");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByRole("heading", { name: "Asistente" })).toBeInTheDocument();
  });
});

describe("navegación desde la landing", () => {
  it("el botón Iniciar sesión de la landing lleva al acceso del portal", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/"]}>
        <StoreProvider>
          <App />
        </StoreProvider>
      </MemoryRouter>
    );

    await user.click(screen.getAllByRole("link", { name: "Iniciar sesión" })[0]);
    expect(await screen.findByRole("heading", { name: "Acceder a mi Portal de Servicio" })).toBeInTheDocument();
  });

  it("una ruta protegida sin sesión redirige al acceso", async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/portal/tickets"]}>
        <StoreProvider>
          <App />
        </StoreProvider>
      </MemoryRouter>
    );
    expect(await screen.findByRole("heading", { name: "Acceder a mi Portal de Servicio" })).toBeInTheDocument();
  });

  it("desde el acceso se llega al registro", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/portal/acceso"]}>
        <StoreProvider>
          <App />
        </StoreProvider>
      </MemoryRouter>
    );
    await user.click(screen.getByRole("link", { name: "Regístrate gratis aquí" }));
    expect(await screen.findByRole("heading", { name: "Crear Cuenta de Cliente" })).toBeInTheDocument();
  });
});

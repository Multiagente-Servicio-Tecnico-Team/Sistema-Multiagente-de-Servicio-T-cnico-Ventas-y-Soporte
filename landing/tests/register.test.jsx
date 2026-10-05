import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Register, { validateRegister } from "../src/pages/portal/Register.jsx";
import { StoreProvider } from "../src/data/store.jsx";
import { ApiError, MESSAGES } from "../src/api/auth.js";

function renderRegister(api) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/portal/registro"]}>
      <StoreProvider>
        <Routes>
          <Route path="/portal/registro" element={<Register api={api} />} />
          <Route path="/portal/tickets" element={<h1>Mis Tickets</h1>} />
        </Routes>
      </StoreProvider>
    </MemoryRouter>
  );
}

async function fillValid(user) {
  await user.type(screen.getByLabelText("Nombre y Apellido"), "Martín Gómez");
  await user.type(screen.getByLabelText("Correo Electrónico"), "martin.gomez@gmail.com");
  await user.type(screen.getByLabelText("Teléfono Móvil"), "987 654 321");
  await user.type(screen.getByLabelText("Contraseña"), "TriageTech#2026");
  await user.type(screen.getByLabelText("Confirmar Contraseña"), "TriageTech#2026");
  await user.click(screen.getByRole("checkbox"));
}

const validForm = { name: "Martín Gómez", email: "m@g.pe", phone: "987654321", password: "TriageTech#2026", confirm: "TriageTech#2026", terms: true };

describe("validateRegister", () => {
  it("acepta un formulario completo", () => {
    expect(validateRegister(validForm)).toEqual({});
  });

  it.each([
    ["password", { password: "corta", confirm: "corta" }],
    ["password", { password: "sinmayuscula#1", confirm: "sinmayuscula#1" }],
    ["confirm", { confirm: "Distinta#2026" }],
    ["phone", { phone: "1234" }],
    ["email", { email: "no-es-correo" }],
    ["terms", { terms: false }],
  ])("marca el campo %s cuando es inválido", (field, patch) => {
    expect(validateRegister({ ...validForm, ...patch })).toHaveProperty(field);
  });
});

describe("pantalla de registro", () => {
  it("muestra errores y no llama a la API si el formulario está vacío", async () => {
    const api = { mode: "api", register: vi.fn() };
    const user = userEvent.setup();
    renderRegister(api);

    await user.click(screen.getByRole("button", { name: /crear mi cuenta/i }));

    expect(screen.getByText("Ingresa tu nombre y apellido.")).toBeInTheDocument();
    expect(screen.getByText("Debes aceptar los términos para continuar.")).toBeInTheDocument();
    expect(api.register).not.toHaveBeenCalled();
  });

  it("actualiza la lista de requisitos de la contraseña", async () => {
    const user = userEvent.setup();
    renderRegister({ mode: "api", register: vi.fn() });

    await user.type(screen.getByLabelText("Contraseña"), "Abc");
    const rules = screen.getByRole("list", { name: /requisitos/i });
    expect(rules.querySelectorAll("li.is-ok")).toHaveLength(1);
    await user.type(screen.getByLabelText("Contraseña"), "defg1#");
    expect(rules.querySelectorAll("li.is-ok")).toHaveLength(4);
    expect(screen.getByText(/Seguridad: Fuerte/)).toBeInTheDocument();
  });

  it("registra con teléfono E.164, abre la sesión y no guarda la contraseña", async () => {
    const api = { mode: "api", register: vi.fn().mockResolvedValue({ nombre: "Martín Gómez", email: "martin.gomez@gmail.com" }) };
    const user = userEvent.setup();
    renderRegister(api);

    await fillValid(user);
    await user.click(screen.getByRole("button", { name: /crear mi cuenta/i }));

    expect(await screen.findByRole("heading", { name: "Mis Tickets" })).toBeInTheDocument();
    expect(api.register).toHaveBeenCalledWith({
      nombre: "Martín Gómez",
      email: "martin.gomez@gmail.com",
      telefono: "+51987654321",
      password: "TriageTech#2026",
    });
    const stored = sessionStorage.getItem("techfix.session");
    expect(JSON.parse(stored)).toEqual({ role: "client", email: "martin.gomez@gmail.com", name: "Martín Gómez" });
    expect(stored).not.toContain("TriageTech");
  });

  it("muestra el error de correo duplicado en el campo correspondiente", async () => {
    const api = { mode: "api", register: vi.fn().mockRejectedValue(new ApiError(MESSAGES.duplicateEmail, { status: 409, field: "email" })) };
    const user = userEvent.setup();
    renderRegister(api);

    await fillValid(user);
    await user.click(screen.getByRole("button", { name: /crear mi cuenta/i }));

    expect(await screen.findByText(MESSAGES.duplicateEmail)).toBeInTheDocument();
    expect(screen.getByLabelText("Correo Electrónico")).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(screen.getByRole("button", { name: /crear mi cuenta/i })).toBeEnabled());
  });
});

import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "../src/App.jsx";
import { StoreProvider } from "../src/data/store.jsx";

const future = { v7_startTransition: true, v7_relativeSplatPath: true };

function renderApp(path, session) {
  if (session) sessionStorage.setItem("techfix.session", JSON.stringify(session));
  return render(
    <MemoryRouter future={future} initialEntries={[path]}>
      <StoreProvider>
        <App />
      </StoreProvider>
    </MemoryRouter>
  );
}

const client = { role: "client", name: "Ana Torres", email: "ana@demo.pe" };

describe("open session", () => {
  it("sign-in redirects to the portal when a customer session exists", async () => {
    renderApp("/portal/acceso", client);
    expect(await screen.findByRole("heading", { name: "Mis Tickets de Atención" })).toBeInTheDocument();
  });

  it("sign-up redirects to the portal when a customer session exists", async () => {
    renderApp("/portal/registro", client);
    expect(await screen.findByRole("heading", { name: "Mis Tickets de Atención" })).toBeInTheDocument();
  });

  it("the landing offers to go back to the portal instead of signing in", () => {
    renderApp("/", client);
    expect(screen.getByRole("link", { name: "Ir a mi portal" })).toHaveAttribute("href", "/portal/tickets");
    expect(screen.queryByRole("link", { name: "Iniciar sesión" })).not.toBeInTheDocument();
  });
});

describe("sign out", () => {
  it("goes back to the landing and protected routes ask for access again", async () => {
    const user = userEvent.setup();
    renderApp("/portal/tickets", client);

    await user.click(screen.getByRole("button", { name: "Menú de usuario" }));
    await user.click(screen.getByRole("menuitem", { name: /cerrar sesión/i }));

    expect(await screen.findByRole("heading", { name: /Cada reparación avanza/ })).toBeInTheDocument();
    expect(sessionStorage.getItem("techfix.session")).toBeNull();

    await user.click(screen.getByRole("link", { name: /Ir al portal del cliente/ }));
    expect(await screen.findByRole("heading", { name: "Acceder a mi Portal de Servicio" })).toBeInTheDocument();
  });
});

describe("new request from the chat", () => {
  it("asks for device and fault, creates the ticket and shows it in Mis Tickets", async () => {
    const user = userEvent.setup();
    renderApp("/portal/asistente", client);

    expect(screen.getByRole("heading", { name: "Nueva Consulta de Diagnóstico" })).toBeInTheDocument();
    expect(screen.getByText(/Hola, Ana/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Mensaje"), "Laptop Lenovo Legion 5{Enter}");
    expect(await screen.findByText(/Ahora describe la falla/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Mensaje"), "Se apaga al abrir juegos{Enter}");
    expect(await screen.findByText("Ticket #TCK-2053 registrado")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Ver en Mis Tickets" }));
    const card = (await screen.findByText("Laptop Lenovo Legion 5")).closest("article");
    expect(within(card).getByText("#TCK-2053")).toBeInTheDocument();
    expect(within(card).getByText(/Recibido/)).toBeInTheDocument();
    expect(within(card).getByText("Por cotizar")).toBeInTheDocument();
  });

  it("an existing ticket opens its conversation with a quote", () => {
    renderApp("/portal/asistente?ticket=TCK-2041", client);
    expect(screen.getByRole("heading", { name: "Diagnóstico Asistido y Cotización Inteligente" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aceptar presupuesto/i })).toBeInTheDocument();
  });
});

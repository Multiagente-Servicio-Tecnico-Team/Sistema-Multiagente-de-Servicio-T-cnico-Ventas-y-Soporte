import { describe, expect, it, vi } from "vitest";
import { ApiError, areaForRole, createAuthApi, MESSAGES, splitFullName, toE164 } from "../src/api/auth.js";

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

describe("authentication client (API mode)", () => {
  it("sends POST /registro with the agreed contract and a normalized email", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(201, { usuario: { id: 1, nombre: "Martín Gómez", email: "martin@demo.pe" } }));
    const api = createAuthApi({ baseUrl: "http://api.local/", fetchImpl });

    const user = await api.register({ firstName: " Martín Gómez ", email: " Martin@Demo.PE ", phone: "+51987654321", password: "Clave#2026" });

    expect(user).toEqual({ id: 1, nombre: "Martín Gómez", email: "martin@demo.pe" });
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://api.local/registro");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ nombre: "Martín Gómez", email: "martin@demo.pe", telefono: "+51987654321", password: "Clave#2026" });
  });

  it("sends POST /login and returns the user without the password", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { usuario: { id: 7, nombre: "Ana", email: "ana@demo.pe" } }));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });

    const user = await api.login({ email: "ana@demo.pe", password: "secreta" });

    expect(fetchImpl.mock.calls[0][0]).toBe("http://api.local/login");
    expect(user).not.toHaveProperty("password");
  });

  it("maps 409 on /registro to an email field error", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(409, { detail: "duplicado" })) });
    await expect(api.register({ firstName: "Ana", email: "a@b.pe", phone: "+51987654321", password: "x" })).rejects.toMatchObject({
      status: 409,
      field: "email",
      message: MESSAGES.duplicateEmail,
    });
  });

  it("maps 401 on /login to wrong credentials without exposing details", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(401, { detail: "usuario no existe" })) });
    const error = await api.login({ email: "a@b.pe", password: "x" }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(MESSAGES.invalidCredentials);
  });

  it("reports a network error when the server does not respond", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockRejectedValue(new TypeError("Failed to fetch")) });
    await expect(api.login({ email: "a@b.pe", password: "x" })).rejects.toMatchObject({ code: "network", message: MESSAGES.network });
  });

  it("uses a generic message for 5xx errors", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(500, { detail: "Traceback ..." })) });
    await expect(api.login({ email: "a@b.pe", password: "x" })).rejects.toMatchObject({ message: MESSAGES.unexpected });
  });
});

describe("authentication client (demo mode)", () => {
  it("rejects an already registered email with 409", async () => {
    const api = createAuthApi({ delay: 0 });
    expect(api.mode).toBe("mock");
    await expect(api.register({ firstName: "Demo", email: "REGISTRADO@techfix.ai", phone: "+51987654321", password: "Clave#2026" })).rejects.toMatchObject({ status: 409 });
  });

  it("does not allow registering the same email twice", async () => {
    const api = createAuthApi({ delay: 0 });
    await api.register({ firstName: "Demo", email: "nuevo@demo.pe", phone: "+51987654321", password: "Clave#2026" });
    await expect(api.register({ firstName: "Demo", email: "nuevo@demo.pe", phone: "+51987654321", password: "Clave#2026" })).rejects.toMatchObject({ field: "email" });
  });
});

describe("backend integration", () => {
  it("sends first and last name separately", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(201, { usuario: { id: 1, nombre: "Martín", apellido: "Gómez", email: "m@g.pe", rol: "CUSTOMER" } }));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });
    await api.register({ firstName: "Martín", lastName: " Gómez ", email: "m@g.pe", phone: "+51987654321", password: "Clave#2026" });
    expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toMatchObject({ nombre: "Martín", apellido: "Gómez" });
  });

  it("logout calls POST /logout and does not fail if the server does not respond", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });
    await expect(api.logout()).resolves.toBeUndefined();
    expect(fetchImpl.mock.calls[0][0]).toBe("http://api.local/logout");
  });

  it("splits the full name and assigns the area by role", () => {
    expect(splitFullName("  María José   Pérez ")).toEqual({ firstName: "María", lastName: "José Pérez" });
    expect(splitFullName("Cher")).toEqual({ firstName: "Cher", lastName: undefined });
    expect(areaForRole("CUSTOMER", "staff")).toBe("client");
    expect(areaForRole("TECHNICIAN", "client")).toBe("staff");
    expect(areaForRole("ADMIN", "client")).toBe("staff");
    expect(areaForRole(undefined, "client")).toBe("client");
  });
});

describe("toE164", () => {
  it("joins prefix and number removing spaces", () => {
    expect(toE164("+51", "987 654 321")).toBe("+51987654321");
  });
});

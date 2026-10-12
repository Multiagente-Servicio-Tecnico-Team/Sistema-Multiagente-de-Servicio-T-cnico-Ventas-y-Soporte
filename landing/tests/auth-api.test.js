import { describe, expect, it, vi } from "vitest";
import { ApiError, areaForRole, createAuthApi, MESSAGES, splitFullName, toE164 } from "../src/api/auth.js";

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

describe("cliente de autenticación (modo API)", () => {
  it("envía POST /registro con el contrato acordado y correo normalizado", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(201, { usuario: { id: 1, nombre: "Martín Gómez", email: "martin@demo.pe" } }));
    const api = createAuthApi({ baseUrl: "http://api.local/", fetchImpl });

    const usuario = await api.register({ nombre: " Martín Gómez ", email: " Martin@Demo.PE ", telefono: "+51987654321", password: "Clave#2026" });

    expect(usuario).toEqual({ id: 1, nombre: "Martín Gómez", email: "martin@demo.pe" });
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://api.local/registro");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ nombre: "Martín Gómez", email: "martin@demo.pe", telefono: "+51987654321", password: "Clave#2026" });
  });

  it("envía POST /login y devuelve el usuario sin la contraseña", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { usuario: { id: 7, nombre: "Ana", email: "ana@demo.pe" } }));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });

    const usuario = await api.login({ email: "ana@demo.pe", password: "secreta" });

    expect(fetchImpl.mock.calls[0][0]).toBe("http://api.local/login");
    expect(usuario).not.toHaveProperty("password");
  });

  it("traduce 409 en /registro a un error del campo email", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(409, { detail: "duplicado" })) });
    await expect(api.register({ nombre: "Ana", email: "a@b.pe", telefono: "+51987654321", password: "x" })).rejects.toMatchObject({
      status: 409,
      field: "email",
      message: MESSAGES.duplicateEmail,
    });
  });

  it("traduce 401 en /login a credenciales incorrectas sin exponer detalles", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(401, { detail: "usuario no existe" })) });
    const error = await api.login({ email: "a@b.pe", password: "x" }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(MESSAGES.invalidCredentials);
  });

  it("informa error de red cuando el servidor no responde", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockRejectedValue(new TypeError("Failed to fetch")) });
    await expect(api.login({ email: "a@b.pe", password: "x" })).rejects.toMatchObject({ code: "network", message: MESSAGES.network });
  });

  it("usa un mensaje genérico ante errores 5xx", async () => {
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl: vi.fn().mockResolvedValue(jsonResponse(500, { detail: "Traceback ..." })) });
    await expect(api.login({ email: "a@b.pe", password: "x" })).rejects.toMatchObject({ message: MESSAGES.unexpected });
  });
});

describe("cliente de autenticación (modo demostración)", () => {
  it("rechaza un correo ya registrado con 409", async () => {
    const api = createAuthApi({ delay: 0 });
    expect(api.mode).toBe("mock");
    await expect(api.register({ nombre: "Demo", email: "REGISTRADO@techfix.ai", telefono: "+51987654321", password: "Clave#2026" })).rejects.toMatchObject({ status: 409 });
  });

  it("no permite registrar dos veces el mismo correo", async () => {
    const api = createAuthApi({ delay: 0 });
    await api.register({ nombre: "Demo", email: "nuevo@demo.pe", telefono: "+51987654321", password: "Clave#2026" });
    await expect(api.register({ nombre: "Demo", email: "nuevo@demo.pe", telefono: "+51987654321", password: "Clave#2026" })).rejects.toMatchObject({ field: "email" });
  });
});

describe("integración con el backend", () => {
  it("envía nombre y apellido separados", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(201, { usuario: { id: 1, nombre: "Martín", apellido: "Gómez", email: "m@g.pe", rol: "CUSTOMER" } }));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });
    await api.register({ nombre: "Martín", apellido: " Gómez ", email: "m@g.pe", telefono: "+51987654321", password: "Clave#2026" });
    expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toMatchObject({ nombre: "Martín", apellido: "Gómez" });
  });

  it("logout llama a POST /logout y no falla si el servidor no responde", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const api = createAuthApi({ baseUrl: "http://api.local", fetchImpl });
    await expect(api.logout()).resolves.toBeUndefined();
    expect(fetchImpl.mock.calls[0][0]).toBe("http://api.local/logout");
  });

  it("separa el nombre completo y asigna el área según el rol", () => {
    expect(splitFullName("  María José   Pérez ")).toEqual({ nombre: "María", apellido: "José Pérez" });
    expect(splitFullName("Cher")).toEqual({ nombre: "Cher", apellido: undefined });
    expect(areaForRole("CUSTOMER", "staff")).toBe("client");
    expect(areaForRole("TECHNICIAN", "client")).toBe("staff");
    expect(areaForRole("ADMIN", "client")).toBe("staff");
    expect(areaForRole(undefined, "client")).toBe("client");
  });
});

describe("toE164", () => {
  it("une prefijo y número quitando espacios", () => {
    expect(toE164("+51", "987 654 321")).toBe("+51987654321");
  });
});

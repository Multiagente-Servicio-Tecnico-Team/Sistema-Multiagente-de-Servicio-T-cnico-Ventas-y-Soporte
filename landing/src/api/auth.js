/*
 * Portal authentication client.
 *
 * - With VITE_API_URL set it calls the backend: POST /registro, /login, /recuperar and /restablecer.
 * - Without VITE_API_URL it uses a local simulator to work on the frontend without a server.
 *
 * Rules: the password only travels in the request body (HTTPS in production); the backend
 * creates the hash. The frontend never stores passwords or tokens: the server session
 * travels in an HttpOnly cookie (hence credentials: "include").
 * The JSON keys (nombre, apellido, telefono, usuario, rol) are the backend contract.
 */
import { resolveApiBaseUrl } from "./baseUrl.js";

export class ApiError extends Error {
  constructor(message, { status = 0, field = null, code = "error" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.field = field;
    this.code = code;
  }
}

export const MESSAGES = {
  network: "No pudimos conectar con el servidor. Revisa tu conexión e inténtalo nuevamente.",
  duplicateEmail: "Este correo ya está registrado. Inicia sesión o recupera tu contraseña.",
  invalidCredentials: "Correo o contraseña incorrectos.",
  invalidData: "Revisa los datos del formulario.",
  tooMany: "Demasiados intentos. Espera un momento antes de volver a intentar.",
  invalidToken: "El enlace no es válido o ya expiró. Solicita uno nuevo.",
  notStaff: "Esta cuenta es de cliente y no tiene acceso al panel del taller. Ingresa por el portal de clientes.",
  unexpected: "Ocurrió un error inesperado. Inténtalo nuevamente.",
};

export function normalizeEmail(email) {
  return String(email).trim().toLowerCase();
}

/** "+51" + "987 654 321" -> "+51987654321" (E.164 format). */
export function toE164(prefix, phone) {
  return `${prefix}${String(phone).replace(/\D/g, "")}`;
}

/** "Martín Gómez Ruiz" -> { firstName: "Martín", lastName: "Gómez Ruiz" } (name and last_name columns). */
export function splitFullName(full) {
  const clean = String(full).trim().split(/\s+/).filter(Boolean);
  return { firstName: clean[0] || "", lastName: clean.slice(1).join(" ") || undefined };
}

export function fullName(user) {
  return [user?.nombre, user?.apellido].filter(Boolean).join(" ");
}

/** Role from the users table -> frontend area. Without a role (demo mode) the screen area is used. */
export function areaForRole(role, fallback) {
  if (role === "CUSTOMER") return "client";
  if (role === "TECHNICIAN" || role === "ADMIN") return "staff";
  return fallback;
}

export function nameFromEmail(email) {
  const local = String(email).split("@")[0].replace(/[._-]+/g, " ").trim();
  return local.replace(/\b\p{L}/gu, (c) => c.toUpperCase()) || "Cliente";
}

function toApiError(path, status, data) {
  if (status === 409 && path === "/registro") return new ApiError(MESSAGES.duplicateEmail, { status, field: "email", code: "duplicate_email" });
  if (path === "/restablecer" && (status === 400 || status === 410)) return new ApiError(MESSAGES.invalidToken, { status, code: "invalid_token" });
  if (status === 401) return new ApiError(MESSAGES.invalidCredentials, { status, code: "invalid_credentials" });
  if (status === 429) return new ApiError(MESSAGES.tooMany, { status, code: "rate_limited" });
  if (status === 400 || status === 422) {
    const field = typeof data?.field === "string" ? data.field : null;
    return new ApiError(MESSAGES.invalidData, { status, field, code: "invalid_data" });
  }
  return new ApiError(MESSAGES.unexpected, { status, code: "unexpected" });
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function createAuthApi({ baseUrl = "", fetchImpl, delay = 450 } = {}) {
  const base = baseUrl.replace(/\/+$/, "");
  const doFetch = fetchImpl ?? ((...args) => globalThis.fetch(...args));

  async function post(path, body) {
    let res;
    try {
      res = await doFetch(`${base}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
    } catch {
      throw new ApiError(MESSAGES.network, { code: "network" });
    }
    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    if (!res.ok) throw toApiError(path, res.status, data);
    return data ?? {};
  }

  if (base) {
    return {
      mode: "api",
      async register({ firstName, lastName, email, phone, password }) {
        const body = { nombre: firstName.trim(), apellido: lastName?.trim() || undefined, email: normalizeEmail(email), telefono: phone, password };
        const data = await post("/registro", body);
        return data.usuario ?? { nombre: body.nombre, apellido: body.apellido ?? null, email: body.email };
      },
      async login({ email, password }) {
        const data = await post("/login", { email: normalizeEmail(email), password });
        return data.usuario ?? { nombre: nameFromEmail(email), email: normalizeEmail(email) };
      },
      async requestPasswordReset({ email }) {
        await post("/recuperar", { email: normalizeEmail(email) });
        return { ok: true };
      },
      async resetPassword({ token, password }) {
        await post("/restablecer", { token, password });
        return { ok: true };
      },
      // Clears the server session cookie; a network failure must not prevent signing out in the browser.
      async logout() {
        try {
          await post("/logout", {});
        } catch {
          /* the local session is closed anyway */
        }
      },
    };
  }

  // Simulator: keeps only registered emails (never passwords) to show the 409 case.
  const registered = new Set(["registrado@techfix.ai"]);
  return {
    mode: "mock",
    async register({ firstName, lastName, email }) {
      await wait(delay);
      const mail = normalizeEmail(email);
      if (registered.has(mail)) throw new ApiError(MESSAGES.duplicateEmail, { status: 409, field: "email", code: "duplicate_email" });
      registered.add(mail);
      return { nombre: firstName.trim(), apellido: lastName?.trim() || null, email: mail };
    },
    async logout() {},
    async login({ email }) {
      await wait(delay);
      const mail = normalizeEmail(email);
      return { nombre: nameFromEmail(mail), email: mail };
    },
    async requestPasswordReset() {
      await wait(delay);
      return { ok: true };
    },
    // The "expirado" token shows the invalid link state without a backend.
    async resetPassword({ token }) {
      await wait(delay);
      if (!token || token === "expirado") throw new ApiError(MESSAGES.invalidToken, { status: 410, code: "invalid_token" });
      return { ok: true };
    },
  };
}

export const authApi = createAuthApi({
  baseUrl: resolveApiBaseUrl(
    import.meta.env?.VITE_API_URL ?? "",
    "/backend/auth",
    import.meta.env?.PROD === true,
  ),
});

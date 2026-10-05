/*
 * Cliente de autenticación del portal (spec 05).
 *
 * - Con VITE_API_URL definido llama al backend: POST /registro, /login, /recuperar y /restablecer.
 * - Sin VITE_API_URL usa un simulador local para trabajar el frontend sin servidor.
 *
 * Reglas: la contraseña solo viaja en el cuerpo de la petición (HTTPS en producción); el hash
 * lo genera el backend. El frontend nunca guarda contraseñas ni tokens: la sesión del servidor
 * debe viajar en una cookie HttpOnly (por eso credentials: "include").
 */

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
  unexpected: "Ocurrió un error inesperado. Inténtalo nuevamente.",
};

export function normalizeEmail(email) {
  return String(email).trim().toLowerCase();
}

/** "+51" + "987 654 321" -> "+51987654321" (formato E.164). */
export function toE164(prefix, phone) {
  return `${prefix}${String(phone).replace(/\D/g, "")}`;
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
      async register({ nombre, email, telefono, password }) {
        const data = await post("/registro", { nombre: nombre.trim(), email: normalizeEmail(email), telefono, password });
        return data.usuario ?? { nombre: nombre.trim(), email: normalizeEmail(email) };
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
    };
  }

  // Simulador: guarda solo correos registrados (nunca contraseñas) para mostrar el caso 409.
  const registered = new Set(["registrado@techfix.ai"]);
  return {
    mode: "mock",
    async register({ nombre, email }) {
      await wait(delay);
      const mail = normalizeEmail(email);
      if (registered.has(mail)) throw new ApiError(MESSAGES.duplicateEmail, { status: 409, field: "email", code: "duplicate_email" });
      registered.add(mail);
      return { nombre: nombre.trim(), email: mail };
    },
    async login({ email }) {
      await wait(delay);
      const mail = normalizeEmail(email);
      return { nombre: nameFromEmail(mail), email: mail };
    },
    async requestPasswordReset() {
      await wait(delay);
      return { ok: true };
    },
    // El token "expirado" permite ver el estado de enlace inválido sin backend.
    async resetPassword({ token }) {
      await wait(delay);
      if (!token || token === "expirado") throw new ApiError(MESSAGES.invalidToken, { status: 410, code: "invalid_token" });
      return { ok: true };
    },
  };
}

export const authApi = createAuthApi({ baseUrl: import.meta.env?.VITE_API_URL ?? "" });

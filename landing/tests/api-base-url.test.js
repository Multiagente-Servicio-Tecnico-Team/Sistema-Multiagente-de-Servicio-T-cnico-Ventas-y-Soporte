import { describe, expect, it } from "vitest";
import { resolveApiBaseUrl } from "../src/api/baseUrl.js";

describe("URL base de cuentas y chat", () => {
  it("usa el proxy del mismo origen si producción no define URL", () => {
    expect(resolveApiBaseUrl("", "/backend/auth", true)).toBe("/backend/auth");
    expect(resolveApiBaseUrl("", "/backend", true)).toBe("/backend");
  });

  it("evita enviar cookies de sesión a un origen externo en producción", () => {
    expect(
      resolveApiBaseUrl(
        "https://backend.example.test/auth",
        "/backend/auth",
        true,
      ),
    ).toBe("/backend/auth");
  });

  it("conserva URLs de desarrollo y rutas relativas de producción", () => {
    expect(
      resolveApiBaseUrl("http://localhost:8000/auth", "/backend/auth", false),
    ).toBe("http://localhost:8000/auth");
    expect(
      resolveApiBaseUrl("/backend/auth", "/backend/auth", true),
    ).toBe("/backend/auth");
  });
});

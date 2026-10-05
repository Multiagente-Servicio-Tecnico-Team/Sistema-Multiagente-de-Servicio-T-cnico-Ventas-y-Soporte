# 05 — Frontend: landing, registro e inicio de sesión (plan y evidencia)

Spec: `spec/05-frontend-landing-auth.md`. Rama: `frontend` (antes `landing-page`).

## Plan de la tarea

1. **Spec 05 — Frontend (esta entrega):** landing, registro, acceso y recuperación en React según Figma;
   cliente HTTP con contrato `/registro` y `/login`; pruebas de interfaz y de contrato.
2. Spec siguiente — Backend: endpoints `POST /registro` y `POST /login`, registro en BD, contraseñas con hash.
3. Spec siguiente — Pruebas de API con Postman (o similar) sobre `/registro` y `/login`.
4. Integración: definir `VITE_API_URL` y validar el flujo completo frontend ↔ backend.

## Implementación

- Pantallas: `landing/src/pages/Landing.jsx`, `pages/portal/Register.jsx`, `pages/portal/Login.jsx`,
  `pages/portal/Recover.jsx`; diseño base en `layouts/AuthLayout.jsx`.
- Cliente de autenticación: `landing/src/api/auth.js` (`createAuthApi`, `ApiError`, `toE164`).
  Con `VITE_API_URL` llama al backend; sin él usa el simulador (`registrado@techfix.ai` simula un correo
  ya registrado para ver el error 409).
- Sesión: `landing/src/data/store.jsx` guarda solo `{ role, name, email }` en `sessionStorage`.
- Configuración: `landing/.env.example`.

Además, la rama conserva las demás pantallas de Figma (portal del cliente y taller) enlazadas desde la landing;
ver la tabla de rutas al final.

## Revisión de la spec y de la lógica (2026-10-05)

Los cuatro criterios de aceptación se cumplían. La revisión del flujo encontró huecos que se corrigieron:

| Hallazgo | Corrección |
| --- | --- |
| La recuperación enviaba un enlace sin pantalla de destino | Nueva pantalla `/portal/restablecer?token=…` (`pages/portal/Reset.jsx`) y contrato `POST /restablecer`; estados de enlace inválido o vencido y de éxito. En modo demostración, botón "Abrir enlace de prueba" (`token=expirado` simula vencido). |
| Acceso y registro seguían visibles con sesión abierta | Redirigen al área del usuario; la landing muestra "Ir a mi portal" / "Ir al panel". |
| "Nueva Consulta / Chat IA" abría siempre el ticket TCK-2041 | El asistente tiene dos modos: consulta nueva (pide equipo y falla, crea ticket "Recibido · En triage" que también aparece en la cola del taller como "Nuevo") y ticket existente (`?ticket=TCK-2041`). |
| Volver a abrir un enlace con otro token conservaba el estado anterior | El formulario se reinicia al cambiar el token. |
| Sin pruebas para recuperación | Pruebas de recuperación, restablecimiento y del contrato `/restablecer`. |

Requisitos de contraseña unificados en `components/PasswordFields.jsx` (registro y restablecimiento).

## Evidencia

```bash
npm --prefix landing install
npm --prefix landing test
npm --prefix landing run build
```

- `npm test`: 5 archivos, **39 pruebas aprobadas** (`landing/tests/`):
  - `recovery.test.jsx` (7): validación del correo, confirmación sin revelar existencia, enlace sin token,
    política de contraseña al restablecer, envío de `{ token, password }`, token vencido y contrato 410.
  - `consultation.test.jsx` (5): redirección de acceso y registro con sesión, enlace "Ir a mi portal",
    consulta nueva que crea el ticket y lo muestra en Mis Tickets, conversación de ticket existente.
  - `auth-api.test.js` (9): URL y cuerpo de `/registro` y `/login`, correo normalizado, `credentials`,
    409 → campo correo, 401 → credenciales, red caída, 5xx sin exponer detalles, duplicados en simulador, E.164.
  - `register.test.jsx` (11): reglas de validación, lista de requisitos en vivo, envío con teléfono E.164,
    sesión sin contraseña, error de correo duplicado en su campo.
  - `login.test.jsx` (7): validación previa, ingreso y redirección, sesión sin contraseña, error 401 con
    reintento, regreso a la ruta protegida, enlace de la landing y redirección sin sesión.
- `npm run build`: sin errores.
- Navegador (Chrome, 1280 px y 390 px): pantallas comparadas con Figma; estado "Creando cuenta…" y error de
  correo duplicado verificados; sin desbordamiento horizontal; sin errores en consola.

## Limitaciones

- Sin backend: el simulador no verifica contraseñas ni persiste usuarios entre recargas.
- La recuperación no envía correos; solo muestra la confirmación.
- Al publicar, el servidor estático debe redirigir todas las rutas a `index.html`.

## Rutas existentes en la rama

| Ruta | Pantalla |
| --- | --- |
| `/`, `/portal/acceso`, `/portal/registro`, `/portal/recuperar`, `/portal/restablecer` | Alcance de esta spec |
| `/portal/tickets`, `/portal/asistente` | Portal del cliente (Figma) |
| `/taller/acceso` | Acceso de personal (creada) |
| `/taller`, `/taller/tickets/nuevo`, `/taller/tickets/:id` | Panel de taller (Figma) |
| `/taller/inventario`, `/taller/inventario/nuevo`, `/taller/inventario/:sku/editar` | Inventario (Figma) |
| `/ayuda`, `*` | Ayuda/FAQ y 404 (creadas) |

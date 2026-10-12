# TechFix.AI — Frontend

Interfaz web de TechFix.AI: landing, registro de cuenta, inicio de sesión y recuperación de contraseña,
más el portal del cliente y el panel del taller. Las pantallas siguen los prototipos de Figma del proyecto.

## Frameworks y librerías

| Uso | Herramienta | Versión |
| --- | --- | --- |
| Interfaz | React | 18.3 |
| Empaquetado y servidor de desarrollo | Vite + `@vitejs/plugin-react` | 5.4 |
| Rutas | React Router | 6 |
| Iconos | lucide-react | 0.460 |
| Pruebas | Vitest + Testing Library + jsdom | 2.1 / 16 / 25 |
| Estilos | CSS propio con variables (sin framework); tipografías Hanken Grotesk y JetBrains Mono | — |

## Estructura de carpetas

```text
landing/
├── index.html               # Documento base y fuentes
├── public/favicon.svg
├── src/
│   ├── main.jsx             # Punto de entrada: router + estado global
│   ├── App.jsx              # Tabla de rutas y protección por rol
│   ├── api/auth.js          # Cliente HTTP de /registro, /login, /recuperar, /restablecer (o simulador)
│   ├── data/store.jsx       # Estado en memoria (tickets, repuestos, sesión) e importes en céntimos
│   ├── layouts/             # AuthLayout (acceso), PortalLayout (cliente), StaffLayout (taller)
│   ├── components/          # Secciones de la landing y piezas comunes (ui, PasswordFields, Logo…)
│   ├── pages/
│   │   ├── Landing.jsx
│   │   ├── portal/          # Login, Register, Recover, Reset, Tickets, Assistant
│   │   ├── staff/           # StaffLogin, Workshop, TicketDetail, NewTicket, Inventory, PartForm
│   │   ├── Help.jsx         # Soporte, preguntas frecuentes, estado y legales
│   │   └── NotFound.jsx
│   ├── styles.css           # Estilos de la landing
│   └── app.css              # Estilos de las pantallas de la aplicación
├── tests/                   # Pruebas Vitest (contrato de API y pantallas de autenticación)
├── .env.example             # VITE_API_URL
└── vite.config.js           # Configuración de Vite y de Vitest
```

## Funcionalidad

| Ruta | Pantalla | Qué hace |
| --- | --- | --- |
| `/` | Landing | Presentación del producto; enlaces al portal, al asistente y al panel |
| `/portal/registro` | Registro | Nombre, correo, teléfono (E.164), contraseña con requisitos en vivo, confirmación y términos |
| `/portal/acceso` | Inicio de sesión | Valida, muestra carga y errores; vuelve a la página protegida solicitada |
| `/portal/recuperar` | Recuperar contraseña | Pide el correo; la respuesta no revela si existe |
| `/portal/restablecer?token=…` | Restablecer contraseña | Nueva contraseña con la misma política; enlace inválido o vencido |
| `/portal/tickets`, `/portal/asistente` | Portal del cliente | Tickets, aprobación de presupuestos y consulta nueva con el asistente |
| `/taller/acceso`, `/taller/*` | Panel del taller | Cola de triage, detalle, ticket presencial e inventario |
| `/ayuda` | Ayuda | Soporte, FAQ, estado del sistema y legales |

Reglas de sesión: las rutas `/portal/*` y `/taller/*` exigen sesión del rol correspondiente; con sesión abierta,
acceso y registro redirigen al área del usuario. La sesión del navegador guarda solo rol, nombre y correo
(`sessionStorage`); nunca contraseñas ni tokens.

## Conexión con el backend

El cliente `src/api/auth.js` decide el modo según `VITE_API_URL`:

- **Sin definir (por defecto):** modo demostración con simulador local. Cualquier correo válido inicia sesión;
  `registrado@techfix.ai` simula un correo ya registrado (409) y `token=expirado` un enlace vencido.
- **Definido:** llama a la API de cuentas ([`app/accounts`](../app/accounts/README.md)) con `POST`, JSON y
  `credentials: "include"` (cookie de sesión HttpOnly).

| Endpoint | Cuerpo | Respuesta esperada |
| --- | --- | --- |
| `/registro` | `{ nombre, apellido, email, telefono, password }` | `201 { usuario }` · `409` correo duplicado · `422` datos inválidos |
| `/login` | `{ email, password }` | `200 { usuario }` + cookie · `401` credenciales · `429` intentos |
| `/logout` | — | `204` y borra la cookie |
| `/recuperar` | `{ email }` | `200` siempre; si la cuenta existe envía el enlace `/portal/restablecer?token=…` por correo |
| `/restablecer` | `{ token, password }` | `200` · `400/410` enlace inválido, vencido o usado · `422` contraseña débil |

`usuario` incluye `rol`: `CUSTOMER` entra al portal del cliente y `TECHNICIAN` o `ADMIN` al panel del taller;
una cuenta de cliente no puede entrar al panel. El campo "Nombre y Apellido" se envía separado en `nombre` y
`apellido`.

Mensajes al usuario: 409 se muestra en el campo correo; 401 como "Correo o contraseña incorrectos"; errores de
red o 5xx con un mensaje genérico, nunca con el texto del servidor.

El asistente usa `src/api/chat.js` y `VITE_CHAT_URL`. Al configurarlo, el portal
envía `POST /api/chat` con la cookie de sesión y el patrón seleccionado
(`hierarchical`, `orchestrator` o `decentralized`); el patrón no cambia hasta
iniciar una conversación nueva. `GET /api/chat/patterns` también requiere sesión.
Sin `VITE_CHAT_URL`, el asistente conserva el flujo de demostración anterior.

## Ejecución local

Requisitos: Node.js 18 o superior (probado con Node 24) y npm.

```bash
npm --prefix landing install
npm --prefix landing run dev
```

Abrir http://localhost:5173. Para usar un backend local, crear `landing/.env` a partir de `.env.example`:

```bash
VITE_API_URL=http://localhost:8000/auth
VITE_CHAT_URL=http://localhost:8000
```

## Pruebas

```bash
npm --prefix landing test
```

57 pruebas en 6 archivos: contrato de cuentas y chat, errores HTTP/red, selector y
bloqueo de patrón, propuestas y tickets, registro, acceso, recuperación,
restablecimiento, roles, cierre de sesión y consulta nueva.

## Compilación y despliegue

```bash
npm --prefix landing run build
```

Genera `landing/dist/` (HTML, CSS y JS estáticos). Para publicarlo:

1. Definir `VITE_API_URL` (incluyendo `/auth`) y `VITE_CHAT_URL` con la URL pública del backend unificado
   **antes** de compilar (Vite las incrusta en el build).
2. Servir `dist/` en cualquier hosting estático (Nginx, Netlify, Vercel, GitHub Pages, S3 + CloudFront…).
3. Configurar la redirección de todas las rutas a `index.html` (aplicación de una sola página), por ejemplo en
   Nginx: `try_files $uri /index.html;`.
4. En el backend, permitir el origen del frontend (CORS con credenciales) y usar HTTPS para que la cookie de
   sesión sea `Secure`.

## Limitaciones actuales

- En modo demostración (sin `VITE_API_URL`) no se verifican contraseñas ni se persisten datos al recargar.
- Tickets, inventario y asistente usan datos de demostración en memoria.
- Sin `VITE_CHAT_URL` el asistente responde con textos de demostración. Con `VITE_CHAT_URL` usa el patrón
  LangGraph configurado (contrato en `app/chat/README.md`); la conversación vive en la pestaña y recargar
  empieza una nueva.

## Chat con los agentes

`/portal/asistente` envía `POST /api/chat` a `VITE_CHAT_URL` con la cookie del inicio de sesión: el cliente no
escribe su correo y el servidor lo identifica por la sesión. Muestra la respuesta del agente, la tarjeta de
presupuesto (aceptar o rechazar) y el ticket creado. Si la sesión terminó lleva al acceso y vuelve al chat; ante
errores temporales ofrece reintentar. Para probarlo con el patrón de referencia:

```bash
VITE_API_URL=http://localhost:8000/auth
VITE_CHAT_URL=http://localhost:8000
```

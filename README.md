# Sistema Multiagente de Servicio Técnico, Ventas y Soporte

TechFix.AI: plataforma para un taller de reparación de equipos. El cliente se registra, inicia sesión y conversa
con agentes LangGraph que diagnostican la falla, consultan repuestos y preparan un presupuesto; el taller atiende
los tickets que se generan.

El proyecto compara tres patrones multiagente con LangGraph, con herramientas y trazabilidad en LangSmith:
**Orquestador/Supervisor**, **Jerárquico** y **Red Descentralizada**. Todos comparten el frontend, las cuentas de
usuario y la base de datos.

## Módulos

| Módulo | Carpeta | Estado |
| --- | --- | --- |
| Landing, portal del cliente y panel del taller (React) | [`landing/`](landing/README.md) | En `main` |
| Cuentas: registro, inicio de sesión, recuperación de contraseña | [`app/accounts/`](app/accounts/README.md) | En `main` |
| Sesión reutilizable y contrato común del chat (`POST /api/chat`) | [`app/chat/`](app/chat/README.md) | En `main` |
| Agente de ventas, soporte y trazas locales | `app/agents/sales.py`, `app/agents/support.py`, `app/tracing.py` | En `main` |
| Patrón de Red Descentralizada (soporte, técnico, ventas con *handoffs*) | `app/agents/decentralized/` | En `main` |
| Patrón Jerárquico | `app/agents/jerarquico/` en la rama `lg-patron-jerarquico` | En su rama |
| Patrón Orquestador/Supervisor | `app/agents/orquestador/` en la rama `alonso_orquestador` | En su rama |
| Correo transaccional (SMTP) | `app/email/` | En `main` |

## Equipo y avance

Estado al 2026-10-05.

| Tarea | Responsable | Rama | Avance |
| --- | --- | --- | --- |
| Landing, registro de cuenta e inicio de sesión | SebasBazauri | `frontend` y `backend`, integradas en `main` | ✅ Completa |
| Patrón de Red Descentralizada | Jose Saldaña | `patron-red-descentralizada`, integrada en `main` | 🟡 Agentes y herramientas listos; falta integración |
| Patrón Jerárquico | jsalinas4 | `lg-patron-jerarquico` | 🟡 Avanzado; pendiente de integrar a `main` |
| Patrón Orquestador/Supervisor | johstevnn | `alonso_orquestador` | 🟡 Avanzado; pendiente de integrar a `main` |

### Landing, registro de cuenta e inicio de sesión — SebasBazauri

- Landing, portal del cliente y panel del taller en React según los diseños de Figma, adaptados a móvil.
- API de cuentas: `/registro`, `/login`, `/logout` y `/me` con bcrypt y PostgreSQL; colección de Postman.
- Recuperación y restablecimiento de contraseña con enlace temporal de un solo uso.
- Sesión reutilizable para los patrones (`SessionGuard`) y contrato común `POST /api/chat`; el asistente del portal
  conversa con el patrón usando la sesión, sin pedir el correo.
- Trabajo previo: agente de ventas con presupuesto `Decimal`, trazas locales y prototipo del portal.
- Pruebas: 56 del frontend (Vitest) y 55 de cuentas, sesión y chat (pytest).

### Patrón de Red Descentralizada — Jose Saldaña

Hecho:

- Agentes de soporte, técnico y ventas que se transfieren la conversación (*handoffs*) con límite de
  transferencias y registro de cada una.
- 7 herramientas `@tool`: estado del ticket, diagnóstico, cotización y transferencias entre agentes.
- Modelo de Groq; trazas en LangSmith mediante las variables `LANGSMITH_*`.
- 35 pruebas: unitarias, de herramientas y una de punta a punta con el modelo real.

Pendiente:

- Agente de almacén e inventario y uso de la base de datos (tickets y repuestos).
- `POST /api/chat` con la sesión del inicio de sesión para conectarlo al portal.

### Patrón Jerárquico — jsalinas4

Hecho:

- Supervisor que delega en los agentes de soporte técnico, ventas y almacén.
- Base de conocimiento (RAG) con el manual de servicio.
- Crea tickets y presupuestos en PostgreSQL (`tickets`, `quotes`) y calcula el presupuesto con repuestos y mano
  de obra.
- Modelo de Groq; trazas en LangSmith con entradas y salidas ocultas.
- API `POST /api/chat` con página de chat propia; 60 pruebas.

Pendiente:

- Traer `main` a su rama y resolver los conflictos en `.env.example`, `.gitignore`, `README.md`, `app/main.py`,
  `app/static/index.html` y `requirements.txt`.
- Identificar al cliente con la sesión del inicio de sesión (hoy lo identifica por el correo escrito en el chat).
- El cálculo del presupuesto es una función del agente; aún no está registrado como herramienta de LangGraph.

### Patrón Orquestador/Supervisor — johstevnn

Hecho:

- Supervisor que orquesta los agentes de atención, técnico, ventas, almacén, cotización y confirmación.
- Base de conocimiento (RAG) de fallas comunes.
- Herramienta `@tool` de inventario; modelo de Groq; configuración de LangSmith.
- Interfaz de consola y de Streamlit; 15 pruebas.

Pendiente:

- Traer `main` a su rama y resolver los conflictos en `.env.example`, `.gitignore`, `README.md`, `app/main.py` y
  `requirements.txt`.
- `POST /api/chat` con la sesión del inicio de sesión (hoy se escribe el correo en la interfaz de Streamlit).

### Integración pendiente del equipo

- Que los tres patrones expongan `POST /api/chat` con `SessionGuard` siguiendo [`app/chat/README.md`](app/chat/README.md),
  para usarlos desde el portal.
- Unificar el acceso a la base de datos: el jerárquico y el orquestador tienen cada uno su propio
  `app/database/repository.py`.
- Acordar una sola forma de calcular presupuestos (catálogo de prueba o repuestos de la base de datos más mano de obra).

## Arquitectura

```text
 Navegador (React + Vite, landing/)
   │  registro, inicio de sesión, recuperación        │  chat del portal (/portal/asistente)
   ▼                                                  ▼
 API de cuentas (app/accounts) ── cookie de sesión ──▶ API del patrón: POST /api/chat
   │  bcrypt, tokens de recuperación                   │  SessionGuard identifica al cliente por la cookie
   ▼                                                  ▼
 PostgreSQL: users · recovery_tokens · tickets · quotes · spare_parts …   ◀── grafo LangGraph del patrón
                                                                             │ herramientas · LangSmith
```

- La identidad del cliente sale siempre de la cookie firmada; el chat nunca pide el correo.
- Cada patrón expone el mismo `POST /api/chat`, así el frontend funciona con cualquiera de ellos. La guía para
  conectar un patrón está en [`app/chat/README.md`](app/chat/README.md).

## Estructura

```text
app/
├── accounts/        API de cuentas (FastAPI): /registro, /login, /logout, /me, /recuperar, /restablecer
├── chat/            Contrato de /api/chat, patrón de referencia y modelo de tickets
├── agents/
│   ├── sales.py     Agente de ventas: presupuesto con el catálogo de prueba (Decimal)
│   ├── support.py   Grafo de soporte del prototipo del portal
│   └── decentralized/  Red descentralizada: agentes, herramientas y grafo
├── database/        Conexión SQLAlchemy a PostgreSQL
├── email/           Servicio SMTP y plantillas
├── main.py          Prototipo del portal (usuarios en variable de entorno)
└── tracing.py       Trazas locales JSONL sin contenido de los mensajes
landing/             Frontend React 18 + Vite
postman/             Colección de la API de cuentas
tests/               Pruebas automáticas (pytest)
```

## Requisitos

- Python 3.12
- Node.js 18 o superior
- PostgreSQL 16 con las tablas del script del equipo (`creacion_tablas_sin_inserciones.sql`)
- Claves de Groq y LangSmith para los patrones con LLM

## Configuración

Copiar `.env.example` a `.env` y completar:

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | `postgresql+pg8000://USUARIO:CLAVE@localhost:5432/techfix` |
| `AUTH_SECRET` | Secreto para firmar la cookie; el mismo en la API de cuentas y en la del patrón |
| `AUTH_SECURE_COOKIE` | `false` solo en `localhost` sin HTTPS |
| `FRONTEND_ORIGINS`, `FRONTEND_URL` | Origen del frontend (`http://localhost:5173`) |
| `MAIL_MODE` | `outbox` guarda los correos en `OUTBOX_DIR`; `smtp` usa las variables `SMTP_*` |
| `GROQ_API_KEY` | Modelo de los agentes de los patrones |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT` | Trazabilidad en LangSmith |

El frontend usa `landing/.env` (ver `landing/.env.example`): `VITE_API_URL` para la API de cuentas y
`VITE_CHAT_URL` para el patrón del chat. Sin ellas funciona en modo demostración.

## Puesta en marcha

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-auth.txt
```

```bash
.venv/Scripts/python -m uvicorn app.accounts.api:create_app --factory --host localhost --port 8000
```

```bash
.venv/Scripts/python -m uvicorn app.chat.reference:create_reference_app --factory --host localhost --port 8001
```

```bash
npm --prefix landing install
```

```bash
npm --prefix landing run dev
```

Abrir http://localhost:5173. Usar `localhost` (no `127.0.0.1`) en todas las URLs para que el navegador envíe la
cookie de sesión a ambas APIs. El puerto 8001 sirve el patrón de referencia; cada patrón del equipo lo reemplaza
con su propia API.

## Pruebas

```bash
npm --prefix landing test
```

```bash
.venv/Scripts/python -m pytest
```

- Las pruebas de `tests/` no usan servicios externos: no necesitan PostgreSQL, SMTP ni claves.
- Las pruebas marcadas `e2e` llaman al modelo real de Groq y se omiten salvo que `GROQ_API_KEY` esté exportada
  en la terminal; para ejecutar solo esas: `pytest -m e2e`.
- `test_database.py` y `test_email.py` (raíz) son scripts manuales que conectan a PostgreSQL y SMTP reales.
- API de cuentas con Postman o Newman: `npx newman run postman/techfix-auth.postman_collection.json`.

## Seguridad

- Contraseñas con bcrypt; nunca se guardan, devuelven ni registran en texto plano.
- Sesión en cookie `HttpOnly` y `SameSite=Lax`, firmada; restablecer la contraseña cierra las sesiones abiertas.
- Importes con `Decimal`; los precios salen del catálogo de prueba.
- Las trazas y los registros no guardan mensajes, credenciales ni textos de excepciones.

## Contribuir

- Una rama por tarea y Pull Request hacia `main`; no subir directamente a `main`.
- Mensajes con *conventional commits*: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Antes de abrir el PR: traer `main` a la rama, resolver conflictos y pasar las pruebas.

## Limitaciones actuales

- Los patrones Jerárquico y Orquestador aún no están en `main` ni usan la sesión del inicio de sesión.
- La Red Descentralizada todavía no expone `POST /api/chat`.
- Tickets, inventario y "Mis Tickets" del frontend usan datos de demostración.
- Conversaciones y límites de intentos viven en la memoria del proceso (una sola instancia).

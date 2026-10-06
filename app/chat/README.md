# Chat del portal — sesión del login y contrato común

El chat del portal (`/portal/asistente` en `landing/`) habla con el patrón LangGraph del equipo mediante
`POST /api/chat`. El cliente se identifica con la cookie de sesión de la API de cuentas, nunca con un correo
escrito en el chat.

| Archivo | Uso |
| --- | --- |
| `app/accounts/session.py` | `SessionGuard`: dependencias `require_customer` y `require_user` para FastAPI |
| `app/chat/contract.py` | Modelos del contrato: `ChatIn`, `ChatOut`, `QuoteOut`, `TicketOut` |
| `app/chat/models.py` | Mapeo de la tabla `tickets` del script de BD |
| `app/chat/reference.py` | Patrón de referencia (grafo atención → soporte técnico → ventas) para probar sin Groq |

## Contrato `POST /api/chat`

Petición (cookie `techfix_session` obligatoria):

```json
{ "conversation_id": null, "message": "Mi laptop HP no detecta el disco", "action": null }
```

`action` puede ser `"accept_quote"` o `"reject_quote"` (botones de la tarjeta de presupuesto). Campos como
`email` o `customer_id` en el cuerpo se ignoran.

Respuesta `200`:

```json
{
  "conversation_id": "…",
  "reply": "Texto del agente",
  "quote": { "status": "proposed", "lines": [{ "label": "SSD de 480 GB", "amount": "180.00" }], "total": "260.00", "currency": "PEN" },
  "ticket": { "code": "TCK-4F2A1C", "status": "QUOTED" }
}
```

| Código | Cuándo |
| --- | --- |
| `401` `session_required` | Sin sesión, cookie inválida o vencida, cuenta inactiva o contraseña cambiada |
| `403` `customer_only` | Usuario de rol técnico o administrador |
| `404` | Conversación inexistente o de otro cliente |
| `409` | Acción sin presupuesto pendiente |
| `422` | Cuerpo inválido (no se repite el mensaje) |
| `429` | Más de 20 mensajes por minuto |
| `503` | Base de datos o modelo no disponibles |

## Cómo adoptarlo en un patrón (Orquestador, Jerárquico o Red descentralizada)

1. Instalar `requirements-auth.txt` y usar el mismo `AUTH_SECRET` y `DATABASE_URL` que la API de cuentas.
2. Crear la guarda e instalar su manejador de errores:

   ```python
   from app.accounts.session import SessionCustomer, SessionGuard
   from app.chat.contract import ChatIn, ChatOut

   guard = SessionGuard.from_env()
   guard.install(app)

   @app.post("/api/chat", response_model=ChatOut, response_model_exclude_none=True)
   def chat(body: ChatIn, customer: SessionCustomer = Depends(guard.require_customer)):
       ...  # usar customer.id en tickets.customer_id y customer.nombre en el saludo
   ```

3. Quitar el campo de correo del cuerpo del chat. En el patrón jerárquico, reemplazar la búsqueda por correo
   (`find_customer`) por el `customer` de la sesión.
4. Responder con `ChatOut`: `reply` siempre; `quote` y `ticket` cuando el grafo los produzca. Importes como texto
   con dos decimales calculados con `Decimal`.
5. CORS con `allow_credentials=True` para los orígenes de `FRONTEND_ORIGINS`.
6. En LangSmith, etiquetar con `customer_id` y `conversation_id`; no enviar correo, nombre ni contraseñas.

## Patrón de referencia

```bash
.venv/Scripts/python -m uvicorn app.chat.reference:create_reference_app --factory --host localhost --port 8001
```

Usa el agente de ventas del repositorio (`app/agents/sales.py`) y su catálogo de prueba. Con un mensaje que
describe el equipo y la falla, crea el ticket en `QUOTED` con el `customer_id` de la sesión; aceptar lo pasa a
`IN_REPAIR` y rechazar a `CANCELLED`. Las conversaciones viven en memoria del proceso.

En el frontend, definir `VITE_CHAT_URL=http://localhost:8001` en `landing/.env` (además de `VITE_API_URL`).
Frontend, API de cuentas y chat deben usar el host `localhost` para que el navegador envíe la cookie.

## Pruebas

```bash
.venv/Scripts/python -m pytest tests/test_session_guard.py tests/test_chat_reference.py -q
```

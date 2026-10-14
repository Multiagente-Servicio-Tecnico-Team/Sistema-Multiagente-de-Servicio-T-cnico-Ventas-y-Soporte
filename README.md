# Sistema multiagente TechFix

## Ejecutar FastAPI

1. Configura `.env` con `GROQ_API_KEY`, `LANGSMITH_API_KEY` y `DATABASE_URL`.
2. Inicia la API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.web:app --host 127.0.0.1 --port 8000
```

La raíz `http://127.0.0.1:8000/` muestra el formulario para ingresar el correo y acceder al chat. La documentación interactiva está en `http://127.0.0.1:8000/docs`; `GET /health` comprueba disponibilidad.

## Flujo HTTP

1. `POST /api/v1/users/identify` con `{"email":"cliente@example.com"}` devuelve el `user_id` real de `users` y un `thread_id` asociado.
2. `POST /api/v1/chat` con `user_id`, `thread_id` y `message` continúa el estado LangGraph de la sesión.

La búsqueda de identidad lee únicamente `id`, `email` y `name`, y filtra usuarios activos. La API valida que el `thread_id` pertenezca al usuario autenticado en el proceso actual.

El chat y las confirmaciones se conservan en memoria por sesión. El RAG se administra en `app/agents/orquestador/knowledge/`; precios y existencias siempre se consultan en PostgreSQL.

# Evidencia 09 — API unificada de cuentas y chat

## Cambio

Se añadió `app.combined:create_app` como punto de entrada. Monta la API de
cuentas en `/auth` dentro de la aplicación del chat, preservando las rutas
`/api/chat` y `/api/chat/patterns`. La fábrica crea una única configuración de
cuentas y comparte con `SessionGuard` la misma fábrica de sesiones SQLAlchemy.
La API de cuentas publica esa fábrica en `app.state.session_factory` para que
la aplicación integrada pueda reutilizarla.

Las URLs configuradas para el frontend local son:

```dotenv
VITE_API_URL=http://localhost:8000/auth
VITE_CHAT_URL=http://localhost:8000
```

Se actualizaron las instrucciones de ejecución y configuración del frontend.
No se añadieron manifiestos ni archivos de despliegue.

## Validación

- `pytest tests/test_combined_api.py tests/test_pattern_api.py tests/test_accounts_api.py -q`: 29 aprobadas.
- `npm --prefix landing test -- tests/register.test.jsx`: 11 aprobadas.
- `npm --prefix landing run build`: aprobado.
- Pylance syntax check de `app/combined.py` y `tests/test_combined_api.py`: sin errores.
- La primera ejecución completa de Vitest tuvo un timeout de 5 segundos en una prueba de registro bajo carga concurrente; la suite dirigida de ese archivo pasó al ejecutarse aislada.

La prueba de integración confirma que una cookie emitida por `/auth/login`
autoriza `GET /api/chat/patterns` en la misma aplicación. La verificación usa
SQLite en memoria y no requiere PostgreSQL, Groq ni LangSmith.

# 03 — Chat del portal

FastAPI sirve el portal y su API. `support_graph` enruta cada mensaje a orientación o ventas. Las respuestas son reglas deterministas en español, sin proveedor LLM ni costo externo. La orientación consulta el historial, pero no extrae automáticamente un diagnóstico o una orden de trabajo.

Endpoints:
- `POST /api/login`: usuario/contraseña; cookie HttpOnly, SameSite=Strict, una hora.
- `POST /api/logout`: revoca sesión.
- `GET /api/messages`: historial del usuario autenticado.
- `POST /api/chat`: mensaje de texto en el campo `message`.
- `POST /api/quotes`: solicitud estructurada de la especificación 01.

Los POST requieren `X-Portal-Request: 1`; el frontend lo envía automáticamente. No se habilita CORS. El portal representa mensajes con `textContent`, sin interpretar HTML.

Usuarios con hashes PBKDF2-SHA256 (600000 iteraciones y salt aleatorio), límites de intentos y errores sin detalles internos. No existen credenciales por defecto. No se reutiliza la tabla usuarios existente porque el repositorio no contiene su modelo ni su mecanismo de autenticación.

Sesiones e historial en memoria (100 mensajes por usuario). Reiniciar borra ambos. Ejecutar un solo worker. Para producción se requiere conectar la identidad real y persistencia compartida; usar HTTPS y cookies Secure.

Pruebas: `python -m pytest tests/test_portal.py -q`.

Prueba de navegador: iniciar `tests/serve_portal.py` con `PYTHONPATH` apuntando a la raíz; ejecutar `node tests/browser.cjs` con Playwright instalado. `BROWSER_CHANNEL=msedge` permite usar Edge local y `PLAYWRIGHT_MODULE` permite indicar la ruta del módulo. El servidor de pruebas usa una cuenta sintética y escucha solo en 127.0.0.1:8765; no usarlo en producción.

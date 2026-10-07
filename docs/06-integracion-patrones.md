# Evidencia 06 — integración de patrones LangGraph

## Resultado

- Se sustituyó el módulo principal roto por una API FastAPI autenticada que expone
  `GET /api/chat/patterns` y `POST /api/chat`.
- La identidad viene de la cookie validada por `SessionGuard`. El cliente no puede
  indicar su propio email o ID como identidad.
- El backend crea/cacha el grafo seleccionado, asocia el `conversation_id` a un
  `thread_id`, bloquea el cambio de patrón dentro de una conversación y evita que
  otro cliente use su ID.
- El contrato compartido normaliza mensajes, patrón, acciones, presupuestos y
  tickets. Las propuestas guardadas no se describen como aceptación de una
  reparación.
- La integración LangSmith transmite tags `service-chat` y `pattern:<id>`, y
  metadatos explícitos de patrón y UUID de conversación. Configura ocultamiento
  de inputs/outputs y reemplaza los textos de error antes de enviarlos al cliente
  de trazas. No añade un ID de cliente a esos metadatos.
- React presenta el selector de patrones, lo bloquea tras iniciar la conversación,
  permite iniciar una conversación nueva y advierte que el patrón Descentralizado
  es experimental y no persiste.
- Se añadieron/ajustaron dependencias del proyecto para que
  `pip install -r requirements.txt` instale el stack de cuentas, LangGraph,
  Groq, LangSmith y Streamlit.
- Se normalizó la URL genérica `postgresql://` de la API de cuentas a
  `postgresql+pg8000://`, coherente con el driver declarado por el proyecto; se
  agregaron pruebas para ambos alias de PostgreSQL y URLs ya explícitas.
- Se migraron las pruebas de la API principal desde el contrato antiguo y se
  adaptaron las pruebas del portal a la nueva API; el script local de servidor
  apunta ahora al objeto `app.main:app`.

## Límites conocidos

- Jerárquico y Orquestador conservan repositorios y formatos internos distintos;
  el backend solamente adapta sus resultados al contrato HTTP común.
- La Red Descentralizada construye su grafo con `MemorySaver`, pero sus
  herramientas son simuladas: no consulta PostgreSQL ni guarda tickets o
  presupuestos. La interfaz informa esta diferencia.
- El registro de ownership de conversaciones, límites de solicitudes y los
  checkpointers están en memoria del proceso. Se requiere una sola instancia y
  se pierde estado al reiniciar.
- No se hicieron solicitudes a Groq, PostgreSQL ni LangSmith reales durante esta
  validación automatizada; en la prueba de arranque posterior se verificó solo
  `SELECT 1` en PostgreSQL, sin invocar agentes ni enviar trazas.
- `npm audit --omit=dev` reportó dos vulnerabilidades moderadas en React Router.
  npm sugiere migrar a la versión mayor 7; no se aplicó un cambio mayor fuera del
  alcance de este bloque.

## Validación

La validación aislada se ejecuta con:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_pattern_api.py tests\test_api.py tests\test_portal.py tests\test_chat_reference.py -q
npm --prefix landing test
npm --prefix landing run build
```

Resultado de validación:

- Backend enfocado: 18 pruebas aprobadas inicialmente; después de añadir cuatro
  pruebas para la normalización del driver, suite aislada completa: 180 pruebas
  aprobadas.
- Frontend Vitest: 57 pruebas aprobadas con `--testTimeout=15000` porque tres
  interacciones de UI superaron el límite de 5 segundos bajo carga local.
- Build Vite de producción: correcto.
- Verificación local de arranque: frontend y OpenAPI de ambas APIs responden
  HTTP 200; catálogo de patrones devuelve 401 sin cookie, como corresponde.
- Conexión PostgreSQL probada con `SELECT 1`; no se imprimió la URL ni datos de
  tablas.
- `pip check`: sin dependencias incompatibles.
- `compileall` sobre `app` y `tests`: correcto.
- Diagnósticos Pylance: sin errores de tipo/sintaxis en los archivos principales
  modificados; el escaneo de imports no encontró módulos sin resolver.
- `git diff --check`: correcto.

La suite indiscriminada `pytest tests` no es segura/aislada: `tests/test_database.py`
y `tests/test_email.py` ejecutan consultas PostgreSQL y autenticación SMTP al
recolectarse. La prueba E2E de Red Descentralizada también llama a Groq real; por
eso estas pruebas quedan excluidas de los comandos locales aislados.

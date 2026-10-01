# Sistema-Multiagente-de-Servicio-Técnico-Ventas-y-Soporte

## Chat multiagente local

El prototipo usa FastAPI para la interfaz web y la API, LangGraph para coordinar
los agentes, Groq como proveedor LLM, LangSmith para trazas y PostgreSQL para
clientes, inventario, tickets y cotizaciones.

### Requisitos previos

- Python 3.10 o posterior.
- PostgreSQL con el esquema descrito en `info.md` ya creado. La aplicación no crea
  ni migra tablas automáticamente.
- Una API key de Groq y el nombre de un modelo habilitado en tu cuenta.
- Una API key de LangSmith si `LANGSMITH_TRACING=true`.
- Un cliente activo con rol `CUSTOMER` y un repuesto activo en `spare_parts` para
  probar el flujo de cotización.

### Esquema PostgreSQL

La base de desarrollo ya tenía tablas y ENUMs en español. Su estructura se
renombró en el mismo sitio al esquema en inglés de `info.md`, preservando filas,
índices, secuencias de identidad y relaciones. La migración de una sola ejecución está en
[`sql/migrate_spanish_schema_to_english.sql`](sql/migrate_spanish_schema_to_english.sql).
No la ejecutes de nuevo después de migrar. Para una base vacía, primero crea el
esquema con el SQL de `info.md`; la aplicación no aplica DDL automáticamente.

### Instalación en Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` sin compartirlo ni subirlo al repositorio. Configura:

- `GROQ_API_KEY` y `GROQ_MODEL`.
- `DATABASE_URL`, por ejemplo
  `postgresql+pg8000://usuario:contraseña@localhost:5432/base`.
- `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true` y `LANGSMITH_PROJECT`.
- `LABOR_HOURLY_RATE` como importe decimal no negativo. No se asume moneda porque
  el esquema SQL define importes `NUMERIC` sin una moneda.

`LANGSMITH_HIDE_INPUTS=true` y `LANGSMITH_HIDE_OUTPUTS=true` están activados en la
plantilla para evitar que los payloads de entrada y salida se registren en trazas.
El proyecto de LangSmith registra metadata con un ID de sesión opaco, no el email.

### Ejecutar

```powershell
uvicorn app.main:app --reload
```

Abre <http://127.0.0.1:8000>. La interfaz solicita el email de un cliente ya
registrado y mantiene el chat en memoria durante la sesión del servidor. Cada
mensaje usa `POST /api/chat`; los datos de conversación no se escriben en
PostgreSQL. El chat primero muestra una evaluación y cotización indicativas: las
guías locales de `docs/knowledge_base/simulated_cases.json` son sintéticas, se
recuperan por coincidencia lexical y sus rangos UM no se usan como precio. Los
totales siempre se calculan con tarifa laboral y precios/stock de PostgreSQL.
No se guarda nada hasta que el cliente responde afirmativamente; entonces se
revalida el inventario y se crean ticket, cotización y detalles en una transacción.
Si cambió el stock o el precio, el chat presenta los valores actualizados y solicita
una nueva confirmación. Un “no” cancela sin insertar datos.

Para ejecutar las pruebas unitarias:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas incluyen recuperación RAG, confirmación de varios turnos, revalidación
de inventario y rollback de la persistencia transaccional. No crean tickets ni
cotizaciones en PostgreSQL real.

### Límite de seguridad del prototipo

El email solo identifica un registro y **no autentica al cliente**. Cualquier
persona que conozca el email de un cliente puede iniciar una sesión como ese
registro. Mantén el prototipo en local o una red de pruebas; antes de exponerlo,
añade autenticación real y autorización por cliente.

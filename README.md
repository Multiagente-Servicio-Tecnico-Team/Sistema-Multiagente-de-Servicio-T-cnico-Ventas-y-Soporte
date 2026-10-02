# Sistema multiagente de servicio técnico, ventas y soporte

Aplicación de chat en español construida con FastAPI y LangGraph. Un supervisor
coordina agentes especializados para evaluar fallas, consultar inventario en
PostgreSQL y presentar cotizaciones. Groq proporciona el modelo de lenguaje y
LangSmith registra trazas de ejecución.

## Arquitectura jerárquica

El supervisor de atención es el punto de coordinación. Decide si debe pedir
aclaraciones, responder una consulta informativa o derivar una solicitud técnica.
Los nodos especialistas realizan tareas acotadas y devuelven resultados al flujo
controlado por el supervisor.

```mermaid
flowchart TD
    Cliente["Cliente / chat web"] --> API["FastAPI"]
    API --> Supervisor["Supervisor de atención"]

    Supervisor -->|Faltan datos| Aclaracion["Solicitar aclaración"]
    Supervisor -->|Consulta general| Informacion["Respuesta informativa"]
    Supervisor -->|Falla técnica| RAG["Recuperación RAG local"]

    subgraph Especialistas["Agentes y servicios especializados"]
        direction TD
        RAG --> Tecnico["Agente de soporte técnico"]
        Tecnico --> Almacen["Agente de almacén y logística"]
        Almacen --> Ventas["Agente de ventas"]
    end

    Almacen <-->|Consultar producto, precio y stock| PostgreSQL[("PostgreSQL")]
    Ventas --> Propuesta["Propuesta indicativa"]
    Propuesta --> Cliente
    Cliente -->|Confirmación| API
    API --> Supervisor
    Supervisor -->|Revalidar propuesta| Almacen
    Ventas -->|Datos confirmados| Persistencia["Persistencia transaccional"]
    Persistencia --> PostgreSQL
    Persistencia --> Respuesta["Ticket y cotización guardados"]
    Respuesta --> Cliente

    Supervisor -. "Clasificación y confirmación" .-> Groq["Groq"]
    Tecnico -. "Diagnóstico estructurado" .-> Groq
    Supervisor -.-> LangSmith["LangSmith"]
    Tecnico -.-> LangSmith
```

## Agentes y responsabilidades

| Agente / componente | Función |
| --- | --- |
| Supervisor de atención | Clasifica la intención, extrae la solicitud, solicita aclaraciones y procesa la confirmación o rechazo de la propuesta. |
| Recuperación de conocimiento | Recupera guías sintéticas relevantes mediante búsqueda lexical local. |
| Soporte técnico | Genera diagnóstico provisional, horas estimadas y repuestos sugeridos en una salida estructurada. |
| Almacén y logística | Consulta productos activos, precio y stock mediante consultas parametrizadas en PostgreSQL. |
| Ventas | Calcula mano de obra y repuestos con `Decimal`, usando la tarifa configurada y los precios actuales de la base. |
| Persistencia | Guarda ticket, cotización, detalles y actualización de estado en una única transacción. |

El LLM no genera SQL ni determina los precios finales. La disponibilidad de un
repuesto se confirma desde PostgreSQL. Si no hay stock, el producto no puede
identificarse de forma inequívoca o cambian los valores antes de confirmar, no se
guarda una cotización desactualizada.

## Flujo de servicio

1. El cliente envía su email registrado y describe el equipo y la falla.
2. El supervisor verifica que exista un cliente activo con rol `CUSTOMER`.
3. La recuperación local busca casos sintéticos de sobrecalentamiento,
   almacenamiento, memoria o batería.
4. El agente técnico presenta un diagnóstico provisional y sugiere horas/repuestos.
5. Almacén consulta los precios y existencias vigentes; ventas calcula la propuesta.
6. El chat presenta la propuesta sin crear registros en PostgreSQL.
7. Si el cliente confirma, se vuelve a comprobar inventario y precio. Si cambió la
   propuesta, se muestran los importes actualizados y se solicita confirmación otra
   vez.
8. Con una confirmación vigente se guardan ticket, cotización y detalles dentro de
   una transacción. Una respuesta negativa no genera escrituras.

Las guías RAG son demostrativas. Sus rangos de coste en UM no se usan en el cálculo
comercial; los totales se calculan con `LABOR_HOURLY_RATE` y los precios de
PostgreSQL.

## Tecnologías

- Python 3.10+
- FastAPI y Uvicorn
- LangGraph y LangChain
- Groq
- LangSmith
- PostgreSQL con SQLAlchemy y `pg8000`
- Pydantic
- `unittest`

## Estructura

```text
app/
├── agents/
│   ├── graph.py             # Grafo jerárquico y flujo de agentes
│   ├── retriever.py         # Recuperación lexical local
│   └── schemas.py           # Contratos estructurados
├── database/
│   ├── connection.py        # Conexión SQLAlchemy
│   └── repository.py        # Consultas y persistencia
├── static/
│   └── index.html           # Interfaz web de chat
├── main.py                  # API FastAPI y sesiones
└── settings.py              # Configuración desde entorno
docs/
└── knowledge_base/
    └── simulated_cases.json # Guías sintéticas RAG
sql/
└── migrate_spanish_schema_to_english.sql
tests/
```

## Requisitos y configuración

Se requiere Python 3.10 o posterior, PostgreSQL accesible con el esquema esperado,
una clave de Groq y un cliente activo registrado con rol `CUSTOMER`. Para activar
trazas también se requiere una clave de LangSmith. La aplicación no crea usuarios
ni instala o migra el esquema automáticamente.

Desde la raíz del repositorio, crea el entorno virtual e instala dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura las siguientes variables localmente en `.env`:

```dotenv
GROQ_API_KEY=tu_clave_groq
GROQ_MODEL=openai/gpt-oss-20b
DATABASE_URL=postgresql+pg8000://usuario:contraseña@localhost:5432/base
LABOR_HOURLY_RATE=10

LANGSMITH_API_KEY=tu_clave_langsmith
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=agente-tecnico
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
```

`LABOR_HOURLY_RATE` es la tarifa por hora de mano de obra configurada para la
aplicación. El esquema de base de datos no establece moneda. No subas `.env` ni
publiques sus claves.

## Ejecución local

Con el entorno virtual activo y `.env` configurado:

```powershell
python -m uvicorn app.main:app --reload
```

Abre <http://127.0.0.1:8000>. Ingresa el email de un cliente activo registrado y
describe la falla, por ejemplo: `Mi laptop está lenta y demora en arrancar`.
Revisa la propuesta; responde `sí` para guardar o `no` para cancelar. Detén el
servidor con `Ctrl+C`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

La suite cubre la API, el flujo del grafo, recuperación RAG, confirmación,
revalidación de precios/stock y transacciones con dependencias simuladas. No crea
cotizaciones de prueba en PostgreSQL.

## API

### `GET /`

Sirve la interfaz web.

### `POST /api/chat`

Envía un mensaje al hilo identificado por un UUID opaco.

```json
{
  "session_id": "2e1c1289-37b8-48ad-8520-74d8a05f7e2c",
  "email": "cliente@example.com",
  "message": "Mi laptop está lenta y demora en arrancar"
}
```

La respuesta incluye `answer` y `outcome`. Antes de confirmar, puede incluir una
cotización indicativa; `ticket_id`, `ticket_code` y `quote_id` solo se entregan
cuando los registros se guardaron correctamente.

## Trazabilidad y privacidad

Con `LANGSMITH_TRACING=true`, las ejecuciones se envían al proyecto configurado. La
metadata usa un ID de sesión opaco, no el email. `LANGSMITH_HIDE_INPUTS` y
`LANGSMITH_HIDE_OUTPUTS` están activados por defecto. Los detalles de errores del
proveedor se redactan antes de enviar la traza; el log local registra el tipo de
error.

## Despliegue y operación

La aplicación se ejecuta como servicio ASGI con Uvicorn. El comando de desarrollo
local es:

```powershell
python -m uvicorn app.main:app --reload
```

Para un proceso Uvicorn sin recarga automática, el comando es:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La configuración de PostgreSQL, Groq, LangSmith y tarifa se proporciona mediante
variables de entorno. El estado conversacional se conserva en memoria del proceso
y desaparece al reiniciarlo; el servicio no persiste sesiones ni comparte estado
entre varias instancias.

El email identifica un registro de cliente y **no autentica** a la persona. El
servicio está destinado a pruebas locales; no lo expongas a una red pública con el
flujo de identificación actual.

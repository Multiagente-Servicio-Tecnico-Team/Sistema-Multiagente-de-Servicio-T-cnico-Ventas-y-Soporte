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
    Supervisor -->|Falla técnica| RAG["Recuperación de manuales Markdown"]

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
| Supervisor de atención | Clasifica la intención, extrae la solicitud, solicita aclaraciones y procesa la confirmación o rechazo de una cotización o ticket técnico. |
| Recuperación de conocimiento | Busca casos en los archivos `.md` de `app/agents/jerarquico/knowledge_base/` y entrega el diagnóstico, la guía técnica y referencias del catálogo al agente técnico. |
| Soporte técnico | Genera un diagnóstico provisional y clasifica el trabajo como diagnóstico si la causa sigue sin identificarse, o como mantenimiento si la tarea ya está determinada. |
| Almacén y logística | Resuelve identificadores contra el código/nombre del catálogo PostgreSQL y valida precio positivo y stock mediante consultas parametrizadas. |
| Ventas | Aplica un precio fijo de mano de obra según la tarea y suma los precios actuales de los repuestos validados en PostgreSQL. |
| Persistencia | Guarda ticket, cotización y detalles en una transacción; los diagnósticos sin repuestos documentados pueden guardar una cotización que cubre solo la mano de obra diagnóstica. |

El LLM no genera SQL ni determina los precios finales. La disponibilidad de un
repuesto se confirma desde PostgreSQL. Si no hay una coincidencia exacta, busca
opciones de la misma familia usando el prefijo del identificador del manual, por
ejemplo `SSD` en `SSD_1TB`. Una única opción disponible puede presentarse como
alternativa sujeta a confirmar compatibilidad; si hay varias, el chat muestra
stock y precio para que se aclare cuál revisar. Sin stock suficiente no se genera
cotización.

## Flujo de servicio

1. El cliente envía su email registrado y describe el equipo y la falla.
2. El supervisor verifica que exista un cliente activo con rol `CUSTOMER`.
3. La recuperación busca síntomas en los casos Markdown y aporta guías técnicas y
   códigos candidatos; `y` requiere los artículos indicados y `o` obliga a elegir
   exactamente una alternativa.
4. El agente técnico presenta un diagnóstico provisional y determina si hay un
   caso documentado en el manual. No estima horas ni precios.
5. Si la causa exacta no está identificada —aunque exista una guía con causas
   posibles— el sistema no cotiza candidatos de repuestos: ofrece abrir un ticket
   y un presupuesto de diagnóstico por S/ 50, con repuestos en S/ 0. Si el trabajo
   o cambio de componente ya está determinado, almacén valida precio y stock en
   PostgreSQL y ventas aplica S/ 40 fijos más los repuestos confirmados.
6. El chat presenta la propuesta sin crear registros en PostgreSQL.
7. Si el cliente confirma, se vuelve a comprobar inventario y precio. Si cambió la
   propuesta, se muestran los importes actualizados y se solicita confirmación otra
   vez.
8. Con una confirmación vigente se guardan ticket, cotización y detalles dentro de
   una transacción. Una respuesta negativa no genera escrituras.
9. En los casos de diagnóstico, el mensaje indica que se creará el ticket, muestra
   S/ 50 de mano de obra, S/ 0 de repuestos y pide confirmación. Solo tras el sí se
   guardan ticket y cotización; al persistir no se insertan filas en `quote_details`.

## Base de conocimiento Markdown

El recuperador lee recursivamente archivos `.md` dentro de
[`app/agents/jerarquico/knowledge_base/`](app/agents/jerarquico/knowledge_base/).
Cada caso debe declarar
`Diagnóstico`, `Solución` y `Componente/Servicio`; se recomienda añadir
`Palabras clave`. Escribe los identificadores de catálogo entre acentos graves y
usa `y` cuando deben consultarse todos o `o` cuando son alternativas:

```markdown
- **Caso 10: Ejemplo de incidencia**
  - **Diagnóstico**: Causa posible que debe verificarse.
  - **Solución**: Referencia técnica para revisar y corregir la incidencia.
  - **Componente/Servicio**: `Servicio_Diagnostico` o `REP-EJEMPLO`.
  - **Palabras clave**: síntoma, equipo, incidencia
```

El manual incluye un caso para laptops lentas que tardan en abrir aplicaciones y
referencia `SSD_1TB` como candidato sujeto a revisión técnica, compatibilidad,
precio y stock. Cuando no se recupera un caso coincidente, el flujo no sugiere
piezas y ofrece una cotización únicamente por diagnóstico.

Cada identificador se busca como código o como parte del nombre en
`spare_parts`. Registra también los servicios como artículos activos del catálogo
con stock suficiente y un precio positivo. El Markdown no crea ni modifica
registros de PostgreSQL, no es fuente de precios y no sustituye la validación de
compatibilidad, inventario y tarifa. Si falta el mapeo del catálogo, no se genera
una cotización.

Los manuales Markdown no contienen tarifas: aportan conocimiento técnico y
referencias del catálogo. Los totales se calculan con los importes fijos
`LABOR_MAINTENANCE_PRICE` o `LABOR_DIAGNOSIS_PRICE` y precios positivos vigentes
de PostgreSQL. Si hay varias alternativas de catálogo, se muestran al cliente sin
elegir una automáticamente; si no hay stock suficiente o el precio es cero, no se
genera cotización de mantenimiento. Si no se puede determinar la causa exacta,
se puede cotizar únicamente el diagnóstico fijo, incluso si una guía relacionada
solo ofrece causas posibles; no se incluyen repuestos hasta que el técnico
determine la reparación.

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
│   └── jerarquico/
│       ├── supervisor.py        # Clasificación y confirmación del cliente
│       ├── technical_support.py # Diagnóstico estructurado
│       ├── warehouse.py         # Validación del catálogo y stock
│       ├── sales.py             # Cálculo y propuesta de cotización
│       ├── persistence.py       # Persistencia y respuesta final
│       ├── knowledge_retrieval.py
│       ├── retriever.py         # Recuperación lexical de manuales Markdown
│       ├── schemas.py           # Contratos estructurados
│       ├── knowledge_base/
│       │   └── manual_servicio.md
│       ├── graph/
│       │   ├── builder.py       # Ensamblaje del grafo jerárquico LangGraph
│       │   ├── routing.py       # Enrutamiento condicional
│       │   └── state.py         # Estado compartido del flujo
│       └── tools/
│           └── quotes.py        # Cálculo determinista con Decimal
├── database/
│   ├── connection.py        # Conexión SQLAlchemy
│   └── repository.py        # Consultas y persistencia
├── static/
│   └── index.html           # Interfaz web de chat
├── main.py                  # API FastAPI y sesiones
└── settings.py              # Configuración desde entorno
docs/
└── implementation-progress.md
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
LABOR_MAINTENANCE_PRICE=40.00
LABOR_DIAGNOSIS_PRICE=50.00

LANGSMITH_API_KEY=tu_clave_langsmith
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=agente-tecnico
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
```

`LABOR_MAINTENANCE_PRICE` y `LABOR_DIAGNOSIS_PRICE` son precios fijos en soles
peruanos (PEN); el primero cubre mantenimiento/cambio de partes y el segundo el
diagnóstico cuando todavía no se identifica la falla. El esquema de base de datos
guarda el importe, pero no una columna de moneda ni una tabla de tarifas. No subas
`.env` ni publiques sus claves.

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

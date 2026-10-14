# Orquestador TechFix

Paquete LangGraph para los nueve agentes definidos en `Patrones.md`. La interfaz existente lo consume con:

```python
from app.agents.orquestador import build_graph, new_thread_id
graph = build_graph()
result = graph.invoke(
    {"messages": [HumanMessage(content="Mi laptop se apaga por temperatura")], "user_id": customer_id},
    {"configurable": {"thread_id": new_thread_id()}},
)
```

## Agentes

1. Atención, triage y FAQ (`customer_service.py`)
2. Ventas (`sales.py`)
3. Soporte hardware (`technical.py`)
4. Soporte software (`technical.py`)
5. Almacén e inventario (`warehouse.py`)
6. Compras y proveedores (`procurement.py`)
7. Facturación y pagos (`payments.py`)
8. Logística y despacho (`logistics.py`)
9. Garantía y postventa (`warranty.py`)

El supervisor enruta por estado, no por clasificación generada libremente. Conversaciones y decisiones pendientes se conservan en `MemorySaver` por `thread_id`. ChatGroq se configura desde `GROQ_API_KEY` y `GROQ_MODEL`; LangSmith lee la configuración existente en `.env`.

## Fuentes RAG

- `knowledge/fallas_comunes.md`: síntomas técnicos y repuestos candidatos ficticios.
- `knowledge/atencion.md`: FAQ/RAG de tienda, servicios, pagos, tarifas, garantías y reglas de atención.
- Los prompts de sistema se declaran en los módulos Python de cada agente y se usan en sus nodos LLM cuando corresponde.

La recuperación se ejecuta localmente sin servicio vectorial. Los datos de inventario, precios y stock se consultan en PostgreSQL y no se toman del RAG.

## Flujos actuales

- FAQ no crea ticket.
- Reparación/soporte: confirmación del cliente, ticket `NEW`, diagnóstico preliminar RAG, consulta de piezas, selección, vista previa y aceptación explícita.
- Venta y PC Build: inventario, opciones, revisión de cotización y aceptación; luego pago pendiente, logística y emisión de garantía.
- Garantía: consulta por código, verificación de vigencia y solicitud/registro de reclamo con ticket original y motivo.
- Compra externa no confirma precio ni orden: el esquema `suppliers` no relaciona proveedores con piezas ni registra costos de cotización.

## Datos ficticios

Dirección y horarios de referencia en `atencion.md` provienen del ejemplo de Patrones.md y deben confirmarse antes de atención real. Los precios y nombres de componentes sólo se obtienen del inventario cargado por SQL.

## Comprobaciones locales

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_confirmation.py tests/test_graph_confirmation.py tests/test_quotes.py tests/test_knowledge_base.py
.\.venv\Scripts\python.exe -m compileall -q app
```

Los scripts raíz `test_database.py` y `test_email.py` ejecutan operaciones externas durante importación y no deben usarse como pruebas unitarias.

# Validación final — 2026-10-02

Entorno: Windows, Python 3.12, LangGraph 1.2.12; dependencias completas instaladas desde `requirements.txt`.

| Orden | Criterio | Evidencia |
| --- | --- | --- |
| 1 | Presupuesto estructurado con datos de prueba | `test_demo_quote`: total PEN 260.00 |
| 1 | Mano de obra y repuestos separados | Listas `labor` y `parts`, subtotales 80.00 y 180.00 |
| 1 | Total coherente | Suma de importes verificada con Decimal |
| 1 | Datos faltantes informados | `missing_data`, `total=null`; pruebas de solicitud vacía y código desconocido |
| 2 | Agentes y herramientas identificables | `sales_agent`, `lookup_catalog`, tipo y jerarquía de llamada |
| 2 | Registros de la misma ejecución | `execution_id`, `run_id`, `parent_run_id`; prueba concurrente |
| 2 | Fallo de prueba registrado | Evento `error` de `failure_probe` en JSONL |
| 2 | Credenciales excluidas | Pruebas con secreto en diagnóstico y excepción; solo metadatos permitidos |
| 3 | Cliente autenticado envía y recibe | API y Edge headless: acceso, mensaje y respuesta visibles |
| 3 | Historial privado | Dos clientes aislados; sesión vencida y logout comprobados |

Resultados:

- `python -m pytest tests/test_sales.py -q`: 3 aprobadas antes de tarea 2.
- `python -m pytest tests/test_tracing.py -q`: 3 aprobadas antes de tarea 3.
- `python -m pytest tests/test_portal.py -q`: 6 aprobadas.
- `python -m pytest -q`: 12 aprobadas en 38.61 s, tras instalar dependencias completas.
- `node tests/browser.cjs`: aprobado con Edge; escritorio 1100×850 y móvil 390×844, sin errores JavaScript ni desbordamiento horizontal.
- `node --check app/static/chat.js`: aprobado.
- `python -m pip check`: sin dependencias rotas.
- `git diff --check`: sin errores de whitespace (avisos de conversión LF/CRLF en Windows).
- `python -m compileall -q app tests`: salida 0, ejecutado después de validar las tres tareas.

Evidencia local: `.local/quote-example.json`, `.local/acceptance-traces.jsonl`, `.local/portal-desktop.png` y `.local/portal-mobile.png`. Los dos primeros se regeneran con `tests/record_examples.py`, usando `PYTHONPATH` en la raíz. Las capturas se regeneran con la prueba de navegador documentada en `03-chat.md`.

No se probaron SMTP ni PostgreSQL contra servicios reales. El portal usa identidad configurable independiente, catálogo de prueba y orientación por reglas. No incluye proveedor LLM, diagnóstico automático, persistencia de conversaciones ni despliegue de producción. El servidor temporal del navegador fue detenido al finalizar.

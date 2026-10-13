# 01 — Ventas del patrón jerárquico

El supervisor comercial deriva consultas de venta directa a almacén y ventas.
El catálogo `spare_parts` es la fuente de stock y precio; `Decimal` se usa para
calcular los importes. El pago solo se crea como `PENDING` después de aceptar la
propuesta. La preferencia de retiro/courier queda como `PENDING_RECEIPT` y no se
presenta como pago, reserva o entrega confirmados.

Para `REPAIR` y `SUPPORT`, el triage registra primero el ticket como `NEW`. Tras
RAG y diagnóstico técnico, el mismo ticket guarda `diagnosis_type` y el campo
`hardware_diagnosis` o `software_diagnosis`, y pasa a `IN_DIAGNOSIS`. Aceptar la
cotización registra `quotes` como `ACCEPTED`, los detalles disponibles, el pago
como `PENDING` y el ticket como `PAYMENT_PENDING` dentro de una transacción.
Rechazarla cancela el ticket sin crear cotización ni pago.

## Casos cubiertos

- Venta directa con coincidencia inequívoca, stock y precio positivos.
- Solicitud de selección explícita si hay varias coincidencias.
- Rechazo de propuesta: cancela el ticket de ingreso y no crea cotización ni pago.
- Aceptación con cotización, detalle y pago pendiente en transacción.
- Actualización idempotente de modalidad logística mientras la recepción sigue
  pendiente; no se permite cambiarla después de la recepción.
- Diagnóstico técnico guardado en el ticket de ingreso, en
  `hardware_diagnosis` o `software_diagnosis` según `diagnosis_type`.
- Aceptación de reparación/soporte con cotización aceptada y pago pendiente en
  transacción; tickets de ingreso ya existentes no se duplican.
- Tarifa predeterminada de mantenimiento/reparación alineada a S/ 35.00 de los
  prompts de servicio. `LABOR_MAINTENANCE_PRICE` sigue permitiendo configurar
  explícitamente otra tarifa.

## Limitaciones del esquema confirmado

- El catálogo no define compatibilidad de piezas entre sí; el agente no presenta
  un armado de PC como cotización verificada.
- No hay relación de producto/proveedor ni oferta de proveedor, por lo que
  compras no inventa precios o plazos.
- No se genera garantía automáticamente: no existe una señal fiable de entrega
  o servicio terminado.
- Un pedido aceptado no descuenta ni reserva existencias.

## Validación

Suite aislada enfocada en repositorio, workflows jerárquicos, grafo, API y
trazabilidad y configuración: **60 pruebas aprobadas**. La conexión a PostgreSQL
local confirmó las columnas `diagnosis_type`, `hardware_diagnosis` y
`software_diagnosis`; no se realizaron escrituras reales. Para reproducir la suite:

```powershell
$env:HIERARCHICAL_TRACE_PATH = Join-Path $env:TEMP 'hierarchical-traces-test.jsonl'
.\.venv-1\Scripts\python.exe -m pytest tests/test_repository.py tests/test_hierarchical_tracing.py tests/test_hierarchical_workflows.py tests/test_multiagent_graph.py tests/test_pattern_api.py tests/test_settings.py -q
Remove-Item -LiteralPath $env:HIERARCHICAL_TRACE_PATH
```

Checkpoint de commit del usuario: ____________________

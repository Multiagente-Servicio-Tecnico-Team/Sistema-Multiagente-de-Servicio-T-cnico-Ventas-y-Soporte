# 02 — Trazabilidad

`invoke_traced` ejecuta los grafos con callbacks locales en `.local/traces.jsonl`.
Cada línea contiene fecha UTC, ejecución, llamada, padre, nombre permitido, tipo y resultado (`start`, `success`, `error`). El resultado registrado es el estado de la llamada; el presupuesto se devuelve al consumidor, no al log.

No se serializan mensajes, parámetros, salidas, metadatos arbitrarios ni excepciones. El contexto desactiva la exportación automática a LangSmith, incluso si el entorno la activa. Usar este punto de entrada para ejecuciones de aplicación.

Pruebas: `python -m pytest tests/test_tracing.py -q`. Incluyen fallo controlado dentro del grafo y ejecuciones concurrentes.

El JSONL es local a una instancia. En despliegue, aplicar permisos del sistema y rotación de archivos; no exponerlo mediante HTTP.

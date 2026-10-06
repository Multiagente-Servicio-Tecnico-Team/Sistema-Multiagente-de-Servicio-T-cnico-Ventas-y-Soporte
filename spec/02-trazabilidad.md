# 02 — Trazabilidad LangGraph

Cada ejecución tiene execution_id; cada llamada run_id y parent_run_id.
Registrar inicio, fin y fallo de grafos, agentes y herramientas en JSONL.
Solo guardar metadatos permitidos, nunca payloads, mensajes, variables de entorno ni textos de errores.
Probar un fallo dentro del grafo y confirmar correlación y ausencia de secretos, incluso con trazado remoto habilitado en el entorno.

# 01 — Ventas

Implementación: `app/agents/sales.py`. Grafo `sales_graph` → `sales_agent`.

Ejemplo de prueba: laptop con SSD averiado confirmado; instalación S/ 80.00 y SSD de 480 GB S/ 180.00, total S/ 260.00. Precios ficticios finales, sin cargos adicionales.

`QuoteRequest` valida límites y cantidades. Una solicitud incompleta devuelve `status=incomplete`, `missing_data` y `total=null`; `known_subtotal` solo suma los conceptos conocidos.

Validación: `python -m pytest tests/test_sales.py -q`.

Referencia de API: https://reference.langchain.com/python/langgraph/graph/state/StateGraph

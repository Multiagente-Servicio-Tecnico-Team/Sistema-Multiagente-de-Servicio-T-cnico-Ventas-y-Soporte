# Evidencia 15 — Catálogo de procesadores, agentes y RAG técnico

## Causa observada y corrección

La salida previa era una respuesta libre del clasificador/ruta informativa: al
elegir `informational`, el grafo terminaba en FAQ sin consultar `spare_parts`.
La instrucción de intake ahora exige que preguntas de catálogo/modelos/stock/
precio vayan a venta. Como protección de la ruta observada, el supervisor
reconduce preguntas informativas identificables de procesadores (serie y
generación/modelo) a una búsqueda comercial parametrizada. La venta conserva
precio/stock del repositorio y sigue esperando selección o aceptación; no
expone SKU.

## Evidencia de catálogo local

Lecturas de solo consulta mediante `find_catalog_items`:

- `procesador i5` devuelve tres productos con stock y precio positivo:
  i5-12400F (S/ 145.00, stock 12), i5-13400F (S/ 210.00, stock 5) e i5-14400
  (S/ 230.00, stock 5).
- `procesador i5 13` devuelve únicamente Intel Core i5-13400F (S/ 210.00,
  stock 5). La lista previa de diez modelos de 13.ª generación no está
  respaldada por este catálogo y no debe repetirse.
- En una coincidencia se genera la propuesta con mano de obra S/ 0.00 y se
  solicita aceptación; con varias, se muestran precios/stock y se espera que
  el cliente elija.

## Auditoría de los nueve roles

| Rol de `contexto/Patrones.md` | Implementación jerárquica |
| --- | --- |
| Atención, Triage y FAQ | `customer_care_supervisor` clasifica y registra; `faq_agent` responde FAQ. |
| Ventas | `sales_agent` calcula la cotización con `Decimal`. |
| Soporte Hardware | `technical_support_agent`. |
| Soporte Software | `software_support_agent`. |
| Almacén e Inventario | `warehouse_agent`, consulta el repositorio de catálogo. |
| Compras y Proveedores | `purchasing_agent` existe, pero no puede cotizar proveedor/artículo: `suppliers` carece de relación con `spare_parts`. |
| Facturación y Pagos | `billing_agent`, guarda cotización aceptada y pago pendiente. |
| Logística y Despacho | `logistics_agent`, registra la preferencia/modalidad. |
| Garantía | `warranty_agent` consulta/reclama; `order_completion_agent` registra la póliza de cierre. |

Los agentes técnico hardware y software pasan por `knowledge_retrieval`, que
recupera secciones pertinentes de los Markdown de `knowledge_base/`; el contexto
recuperado se adjunta al prompt de cualquiera de los dos agentes. El set de
pruebas cubre un caso RAG de hardware y otro de soporte software. No son dos
índices separados: comparten el recuperador y el manual técnico.

Los supervisores de equipo son nodos deterministas de enrutamiento/etiquetado
(`team`), no agentes LLM que elijan herramientas. Todos los nueve roles están
representados en el grafo, con la limitación indicada para Compras.

## Validación

- Regresión del clasificador `informational` a venta de procesador con
  confirmación/precio desde catálogo.
- Caso software 0x0000007B recupera `manual_servicio:002`; caso hardware existente
  recupera su guía y genera la consulta de inventario correspondiente.
- Lectura local de PostgreSQL, sin escrituras ni cambios de inventario.
- Suites enfocadas jerárquicas, grafo, repositorio y trazabilidad: 59 aprobadas;
  `git diff --check` limpio.

Checkpoint de commit del usuario: ____________________

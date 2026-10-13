# Spec 12 — Consulta comercial de catálogo y RAG técnico

## Objetivo

Evitar que las preguntas sobre procesadores/modelos/precios actuales se
respondan con información recordada o inventada; consultar el inventario real y
permitir avanzar a una compra. Confirmar además la cobertura RAG de soporte
hardware y software y el inventario de los nueve roles del patrón.

## Requisitos

1. Una pregunta de catálogo de procesador que el clasificador etiquete como
   informativa debe reconducirse a una consulta comercial, si incluye un modelo
   o familia identificable y una señal de consulta de catálogo/disponibilidad.
2. La búsqueda debe conservar familia, serie y generación/modelo solicitados,
   consultar `spare_parts` mediante el repositorio y filtrar activos con precio
   positivo y stock suficiente. No mostrar resultados recordados, inventar
   variantes, precio ni stock, ni exponer SKU.
3. Con varias coincidencias, presentar nombre, precio y stock para que el
   cliente seleccione por nombre o número. Con una coincidencia, presentar el
   precio cotizado y pedir aceptación explícita; la venta directa mantiene mano
   de obra S/ 0.00.
4. Soporte hardware y software deben recuperar contexto Markdown pertinente
   antes de su agente especializado, y cada agente debe recibir ese contexto en
   su prompt.
5. Mantener los nueve roles del patrón: Atención/Triage/FAQ, Ventas, Soporte
   Hardware, Soporte Software, Almacén, Compras, Facturación, Logística y
   Garantía.

## Fuera de alcance y limitaciones

- No se agregan productos ni se fabrican los nueve modelos de 13.ª generación
  citados por la respuesta previa. La base de datos actual es la autoridad.
- `suppliers` no tiene relación con `spare_parts` ni precio de compra; el rol
  Compras existe, pero no puede calcular una cotización/proveedor por producto.
- Los supervisores de equipo actuales aplican enrutamiento determinista y
  etiquetan el equipo; no son supervisores LLM delegadores.

## Criterios de aceptación

- Consulta de Intel Core i5 de 13.ª generación llega al inventario, no al FAQ,
  muestra solo el producto del catálogo que satisface la búsqueda y solicita
  aceptación antes de guardar la cotización.
- La regresión prohíbe enumerar como disponibles modelos ausentes del catálogo.
- Una solicitud de software relevante entrega documentos RAG al agente de
  software; las pruebas de reparación hardware verifican la recuperación para
  el agente hardware.

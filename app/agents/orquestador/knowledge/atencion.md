# Base RAG de atención y preguntas frecuentes de TechFix

Este documento es la fuente local de respuestas informativas del Agente 1. Los datos específicos de dirección y horario que aparecen aquí provienen del ejemplo de `contenido/Patrones.md`; deben confirmarse con el negocio antes de usarse como información comercial definitiva. Si el dato está marcado como referencia o no está confirmado, el agente debe decirlo con claridad.

## Ubicación de la tienda y recepción de equipos
Dirección de referencia incluida en Patrones.md: Av. Principal #123, Oficina 201, a dos cuadras del centro comercial. Es un ejemplo para el flujo, no una dirección verificada. No inventar distrito, coordenadas, enlace de mapas, teléfono ni referencias adicionales. Antes de que el cliente se dirija al local, advertir que debe confirmar la dirección y disponibilidad de recepción con el negocio.

## Horarios de atención
Horario de referencia de Patrones.md: lunes a sábado, de 9:00 a. m. a 7:00 p. m. El documento no define horario de días festivos, feriados ni excepciones. Presentarlo como horario de referencia sujeto a confirmación; no afirmar que la tienda está abierta en una fecha concreta.

## Servicios que ofrece TechFix
El flujo contempla diagnóstico y reparación de equipos, soporte de hardware, soporte de software, armado de PC a medida, venta directa de componentes/periféricos, consulta de inventario, recepción de equipos y coordinación de retiro o envío por courier. El diagnóstico es preliminar hasta la inspección física cuando corresponda. No prometer servicio remoto, disponibilidad inmediata, reservas ni fecha de entrega sin confirmación del sistema/operación.

## Tarifas de mano de obra
La tarifa de referencia para reparación/soporte técnico es S/ 35.00. El armado de PC contempla S/ 50.00 por ensamble, organización de cableado y pruebas. Son tarifas descritas por el patrón de negocio; informar que son de referencia y validar vigencia antes de comprometer un presupuesto. Los repuestos se cotizan con precios actuales de PostgreSQL, no con este documento.

## Medios de pago
El ejemplo de Patrones.md enumera efectivo, tarjetas de crédito/débito, transferencia bancaria y billeteras digitales Yape/Plin. La disponibilidad real de cada medio debe confirmarse con el negocio al momento del pago. El sistema puede generar una orden de pago con estado PENDING; eso no significa que el pago haya sido recibido o conciliado. Nunca solicitar números de tarjeta, claves, códigos de seguridad, tokens ni credenciales en el chat.

## Términos generales de garantía
El flujo define una duración objetivo de tres meses (`warranty_months = 3`) para las pólizas emitidas tras una venta o servicio elegible, desde su fecha de inicio registrada. La cobertura concreta corresponde al artículo/servicio y a los términos guardados en la póliza. Los patrones no especifican exclusiones, condiciones de manipulación, consumibles ni alcance legal; no inventarlos ni asegurar que cualquier daño está cubierto.

Para consultar vigencia se necesita el código exacto `WAR-...`; Atención deriva la consulta al Agente 9, que verifica estado y fecha en PostgreSQL. Una póliza activa no implica aprobación automática de un reclamo. Los reclamos válidos quedan `IN_REVIEW` y sujetos a evaluación/inspección. No crear ticket ni reclamo al responder una pregunta general de política; sí iniciar el flujo de garantía cuando el usuario pida consultar su póliza o presentar un reclamo.

## Proceso de reparación y cotización
Atención recopila equipo/modelo y síntomas, explica el siguiente paso y solicita confirmación antes de registrar una solicitud. Luego el equipo especializado formula un diagnóstico preliminar, Almacén verifica existencias y Ventas presenta el desglose. Una cotización no reserva inventario y sólo se registra después de la aceptación explícita del cliente. Los precios y stock actuales se obtienen de PostgreSQL.

## Armado de PC a medida
Ventas recoge presupuesto y uso esperado, propone componentes compatibles, consulta inventario y permite ajustar la configuración. Cada cambio de componente exige volver a consultar el inventario y recalcular. El presupuesto máximo indicado no equivale a aceptación. La mano de obra de ensamble de referencia es S/ 50.00; la selección final requiere aprobación expresa.

## Venta directa de componentes
La venta directa incluye repuestos, componentes y periféricos. La disponibilidad y el precio se confirman mediante la consulta en vivo de `spare_parts`. Si hay alternativas compatibles, se presentan para que el cliente elija; no se sustituye una pieza silenciosamente. Una cotización aceptada genera una orden de pago pendiente y luego se coordina retiro o envío.

## Retiro, recepción y envíos por courier
El patrón permite registrar retiro/atención presencial (`PHYSICAL_STORE`) o envío/recepción por courier (`COURIER_SHIPMENT`). La elección logística queda inicialmente `PENDING_RECEIPT`; no confirma recepción, despacho ni entrega. Para courier se solicitan únicamente los datos necesarios. No inventar precio de envío, empresa, tracking, dirección real del taller ni fecha de entrega. La dirección de referencia indicada arriba no está verificada.

## Reembolsos y cancelaciones
El esquema contempla solicitudes de reembolso para evaluación administrativa, pero la intención `REFUND` no está admitida por el enum de tickets de referencia. Atención no debe crear un tipo de ticket inválido, aprobar devoluciones ni afirmar que un reembolso fue procesado. Debe explicar la limitación y derivar al canal administrativo configurado.

## Cómo responder preguntas frecuentes
Usa sólo los fragmentos recuperados de esta base para información de tienda, horarios, tarifas y políticas generales. Distingue referencias de datos confirmados. Si algo no está descrito, dilo en vez de completar con una suposición. Las preguntas generales no crean registros. Si el usuario pasa de una pregunta a pedir una reparación, compra, armado, consulta de póliza o reclamo, clasifica esa nueva intención y sigue su flujo específico de `contenido/Patrones.md`.

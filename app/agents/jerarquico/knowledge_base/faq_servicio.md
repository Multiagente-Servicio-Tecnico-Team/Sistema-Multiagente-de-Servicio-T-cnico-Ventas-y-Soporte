# Preguntas frecuentes de servicio — datos de demostración

> **Aviso:** este documento contiene información ficticia para probar el
> asistente en un escenario peruano. La dirección, el horario y los datos
> operativos de abajo no identifican un negocio real ni deben usarse para
> visitar, enviar equipos o realizar pagos. Sustituirlos por información
> confirmada antes de publicar el sistema.

## Servicios disponibles

¿Qué servicios ofrecen? TechFix brinda, como escenario de demostración:

- Diagnóstico y reparación de computadoras y laptops (hardware).
- Soporte de sistemas operativos, aplicaciones y controladores (software).
- Mantenimiento y cambio de repuestos, sujeto a evaluación técnica y stock.
- Venta directa de repuestos y componentes incluidos en el catálogo conectado.
- Orientación para armado de PC: perfiles de oficina/estudio o juegos sujetos al
  presupuesto y a los componentes que existan en el catálogo. El cliente puede
  cambiar componentes antes de aceptar y recibir una cotización actualizada.
  Algunos datos de compatibilidad (por ejemplo, largo/conectores de GPU, BIOS y
  potencia real) requieren cotejo con el fabricante; no presentar los perfiles
  como garantía de compatibilidad integral.
- Consulta de vigencia y registro de reclamos de garantía, sujetos a la póliza
  existente y a la revisión del equipo.

El diagnóstico conversacional es preliminar y no reemplaza la inspección del
técnico. Para iniciar reparación o soporte, Atención registra un ticket `NEW`;
el técnico agrega el diagnóstico y lo pasa a `IN_DIAGNOSIS`. Una cotización se
guarda solo después de que el cliente la acepte. Si la rechaza, el ticket se
cancela y no se registra el cobro.

## Tarifas de mano de obra

Importes de referencia para la configuración local de demostración:

| Servicio | Tarifa predeterminada |
| --- | ---: |
| Mantenimiento o reparación con trabajo determinado | S/ 35.00 |
| Diagnóstico cuando aún no se identifica el trabajo o repuesto | S/ 50.00 |
| Armado de PC | S/ 50.00 |
| Mano de obra en venta directa de artículos | S/ 0.00 |

Las tarifas de mantenimiento, diagnóstico y armado se calculan con la
configuración del servidor y pueden tener un valor distinto si se configuró un
override. El servidor es la fuente vigente; si el importe calculado por el
sistema difiere de esta tabla, mostrar el importe de la cotización generada y
no prometer la tarifa de referencia.

La tarifa de diagnóstico cubre solo el diagnóstico, no repuestos ni una
reparación posterior. En otras cotizaciones, el total suma la mano de obra
aplicable y los repuestos identificados. Los precios de productos y repuestos
se consultan en el catálogo activo; no inventar precios, descuentos, stock,
marcas disponibles ni costos de proveedor.

## Ubicación y horario — simulados

Solo para pruebas conversacionales: la tienda ficticia se ubica en **Av. Los
Circuitos 404, distrito ficticio de TechFix, Lima, Perú**. Dirección de
demostración; no existe confirmación de que sea un local real ni debe usarse
para llevar o enviar equipos.

Horario de atención simulado: lunes a viernes de 09:00 a 18:00 y sábados de
09:00 a 13:00 (hora de Perú, UTC-5); domingos y feriados cerrado. Estos horarios
son datos de prueba, no una promesa de atención efectiva.

## Pagos y cotizaciones

El cliente recibe la cotización en soles peruanos (S/). El sistema registra una
cotización como `ACCEPTED` y una orden de pago como `PENDING` solo después de la
aceptación explícita. `PENDING` significa que el pago aún no está confirmado:
no afirmar que se recibió dinero, emitir comprobante, reservar inventario ni
autorizar despacho.

Los medios de pago y los datos de transferencia no están configurados. No
solicitar números de tarjeta, claves, códigos de seguridad ni credenciales; no
afirmar que Yape, Plin, transferencia u otro medio está habilitado.

## Garantía

La referencia general de demostración es una duración objetivo de tres meses,
pero no confirma cobertura. La vigencia individual se consulta con el código
exacto de la póliza vinculada a la cuenta del cliente. La cobertura final de un
reclamo requiere revisar la póliza y evaluar el equipo; no prometer aprobación,
reparación gratuita ni reembolso antes de esa evaluación.

## Retiro, recepción y envíos

Se puede registrar como preferencia el retiro presencial o el envío por courier.
Elegir una modalidad no confirma recepción del equipo, pago, reserva, despacho,
seguimiento, costo ni fecha de entrega. Los datos de recepción y envío solo se
solicitan cuando el flujo correspondiente los necesite.

## Compras y disponibilidad

La disponibilidad y los precios de repuestos se consultan en el inventario
actual. Si no hay stock, el sistema puede informar alternativas disponibles,
pero el técnico debe validar compatibilidad. No se dispone de cotizaciones
verificables de proveedores ni de plazos de abastecimiento en este escenario;
no inventar proveedor, precio externo o fecha de entrega.

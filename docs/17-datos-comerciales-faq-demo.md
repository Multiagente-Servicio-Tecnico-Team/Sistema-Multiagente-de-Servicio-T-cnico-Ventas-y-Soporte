# Evidencia 17 - datos comerciales FAQ

Se añadió a `faq_servicio.md` la presencia de tienda y una ubicación/horario de
demostración para Perú. Las preguntas de ubicación recuperan el párrafo con la
dirección; las preguntas de horario recuperan la agenda de atención. El RAG
mantiene un comentario HTML interno indicando que los datos son de demostración
y deben reemplazarse antes de producción; ese preámbulo no se recupera como
sección para la respuesta conversacional.

El retiro presencial conserva su significado de preferencia logística, por lo
que el asistente no declara recibido el equipo solo porque el cliente eligió
esa modalidad. Los datos de pago siguen sin configurarse.

Validación: pruebas FAQ y workflows enfocadas; sin consultas ni escrituras a
PostgreSQL. La dirección y horario son ficticios y no verifican un local real.

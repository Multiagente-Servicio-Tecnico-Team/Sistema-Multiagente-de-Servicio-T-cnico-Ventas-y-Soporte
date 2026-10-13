# Spec 14 - datos comerciales de FAQ para demostración

## Objetivo

Responder preguntas habituales sobre los servicios y la tienda física del
escenario TechFix con información concreta cargada en el RAG de FAQ.

## Requisitos

- La FAQ debe responder afirmativamente que hay tienda física e indicar Av.
  Los Talleres 450, San Borja, Lima, Perú.
- Informar atención de lunes a viernes de 09:00 a 18:00 y sábados de 09:00 a
  13:00, hora local de Lima; domingos y feriados cerrado.
- Relacionar retiro presencial con esa ubicación y aclarar que seleccionar el
  retiro registra una preferencia, no confirma la recepción física.
- Mantener respuestas veraces para pagos, precios, garantía e inventario según
  fuentes dinámicas o configuración existentes; no inferir datos operativos
  adicionales a partir de la dirección.
- Mantener el contenido identificado internamente como dato de demostración,
  para sustituirlo antes de publicar información comercial real.

## Limitaciones

La dirección y el horario son inventados para el escenario local de prueba y no
deben emplearse para visitas reales. El sistema no valida mapas, courier ni
presencia efectiva en el domicilio indicado.

# Spec 16 - precios y deduplicación del seed de inventario

## Objetivo

Mejorar el catálogo de demostración usado para ventas, con precios de referencia
en soles peruanos y menos filas redundantes por familia de componentes.

## Requisitos

- Revisar precios de componentes con fuentes comerciales peruanas y expresar
  importes en PEN.
- Mantener alternativas por marca cuando representen opciones reales de compra;
  no multiplicar filas solo por cambiar frecuencia cuando el seed no especifica
  un número de parte distinto.
- Eliminar filas de producto repetidas entre los bloques inicial y ampliado.
- Conservar el stock/precio solo como dato de demostración sujeto a actualización.
- No modificar una base conectada al editar el archivo de inserción.
- Documentar que `ON CONFLICT (code) DO NOTHING` no actualiza filas existentes.

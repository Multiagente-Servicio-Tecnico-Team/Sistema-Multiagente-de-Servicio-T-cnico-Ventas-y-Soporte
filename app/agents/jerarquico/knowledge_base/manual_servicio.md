# Manual de resolución de problemas típicos y catálogo sugerido

Este manual ofrece referencias de diagnóstico para casos frecuentes. Los códigos
de `Componente/Servicio` identifican candidatos que deben existir en
`spare_parts` de PostgreSQL como artículos activos, con stock disponible y precio
mayor que cero. Los precios y el stock se consultan siempre en la base de datos;
este documento no contiene tarifas. Los procedimientos son referencias internas
para personal técnico, no instrucciones de reparación para el cliente.

## Problemas de arranque y encendido

- **Caso 1: PC enciende pero la pantalla queda negra o muestra "No Signal"**
  - **Diagnóstico**: RAM mal colocada, GPU suelta o BIOS desconfigurada.
  - **Solución**: El técnico debe revisar conexiones, memoria y configuración de BIOS con el equipo desconectado.
  - **Componente/Servicio**: `Servicio_Mantenimiento_Contactos` y `Pila_CR2032`.
  - **Palabras clave**: pantalla negra, no signal, enciende, sin imagen, RAM, BIOS

- **Caso 2: Pantalla azul 0x0000007B (INACCESSIBLE_BOOT_DEVICE)**
  - **Diagnóstico**: Controlador de disco incorrecto, modo SATA cambiado o datos de arranque dañados.
  - **Solución**: El técnico debe verificar el modo de almacenamiento y diagnosticar el arranque antes de reparar el sistema.
  - **Componente/Servicio**: `Servicio_Recuperacion_Sistema`.
  - **Palabras clave**: pantalla azul, 0x0000007B, inaccessible boot device, no inicia, arranque

- **Caso 3: PC se apaga poco después de encender**
  - **Diagnóstico**: Posible fallo de fuente, cortocircuito o problema de montaje en la placa base.
  - **Solución**: El técnico debe aislar la causa con equipo y procedimientos de diagnóstico seguros; no indicar pruebas eléctricas caseras.
  - **Componente/Servicio**: `Servicio_Aislamiento_Placa` o `Fuente_Poder`.
  - **Palabras clave**: se apaga, apagado inmediato, fuente, cortocircuito, placa base

- **Caso 4: Windows se congela en el logo durante el arranque**
  - **Diagnóstico**: Archivos de inicio dañados o unidad de almacenamiento degradada.
  - **Solución**: El técnico debe diagnosticar la unidad y el entorno de recuperación antes de reparar el sistema o reemplazar componentes.
  - **Componente/Servicio**: `SSD_1TB` o `Servicio_Recuperacion_Sistema`.
  - **Palabras clave**: congelado, logo de Windows, no inicia, arranque bloqueado, disco

## Rendimiento, memoria y temperatura

- **Caso 5: Uso de disco al 100% y equipo lento**
  - **Diagnóstico**: Servicio de indexación o almacenamiento mecánico degradado; confirmar estado de la unidad.
  - **Solución**: El técnico debe revisar procesos de inicio y salud del almacenamiento; proponer cambio de unidad solo tras verificar compatibilidad.
  - **Componente/Servicio**: `SSD_1TB`.
  - **Palabras clave**: disco al 100, laptop lenta, computadora lenta, hdd, arranque lento, tarda en iniciar

- **Caso 6: CPU al 100% sin aplicaciones abiertas**
  - **Diagnóstico**: Posible controlador o periférico incompatible, actividad de fondo o interrupciones del sistema.
  - **Solución**: El técnico debe aislar el controlador o dispositivo causante y validar actualizaciones compatibles.
  - **Componente/Servicio**: `Servicio_Optimizacion_Drivers`.
  - **Palabras clave**: CPU al 100, system interrupts, procesador, controlador, driver

- **Caso 7: Frecuencia de CPU baja por temperatura elevada**
  - **Diagnóstico**: Ventilación obstruida, pasta térmica degradada o ventilador con rendimiento irregular.
  - **Solución**: El técnico debe inspeccionar y limpiar el sistema de refrigeración y sustituir consumibles si el diagnóstico lo confirma.
  - **Componente/Servicio**: `Pasta_Termica` y `Ventilador_CPU`.
  - **Palabras clave**: sobrecalentamiento, temperatura alta, se calienta, ventilador ruidoso, se apaga, thermal throttling

- **Caso 8: Memoria RAM casi llena en reposo**
  - **Diagnóstico**: Posible fuga de memoria de un controlador o software de red problemático.
  - **Solución**: El técnico debe identificar el proceso y controlador implicados antes de limpiar el software o recomendar ampliación de memoria.
  - **Componente/Servicio**: `Servicio_Limpieza_Software` o `RAM_16GB`.
  - **Palabras clave**: memoria al 90, RAM, memory leak, fuga de memoria, poca memoria

## Energía y batería

- **Caso 9: Laptop no carga o la batería dura poco**
  - **Diagnóstico**: Batería degradada, cargador o conector defectuoso, o fallo de gestión de energía.
  - **Solución**: El técnico debe probar cargador, conector y batería; reemplazar la batería solo tras confirmar el diagnóstico y el modelo.
  - **Componente/Servicio**: `REP-BAT-L2023`.
  - **Palabras clave**: batería, no carga, no retiene carga, se descarga rápido, cargador

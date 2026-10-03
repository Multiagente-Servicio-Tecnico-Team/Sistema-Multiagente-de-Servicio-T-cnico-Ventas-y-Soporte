# Memoria del proyecto

- Base inicial: Python, correo SMTP y conexión SQLAlchemy; sin API ni portal.
- Se conservan los servicios existentes. El nuevo flujo no depende de ellos.
- Orden acordado: ventas → trazabilidad → chat → validación y compilación final.
- Catálogo local de demostración, moneda PEN, precios finales sin impuestos adicionales.
- Tarea 1 completada: grafo de ventas y herramienta de catálogo; 3 pruebas aprobadas.
- Tarea 2 completada: callbacks JSONL, llamadas correlacionadas, fallo controlado y concurrencia; 3 pruebas aprobadas.
- Tarea 3 completada: portal FastAPI, sesiones y usuarios con hashes; 6 pruebas aprobadas.
- Prueba real en Edge headless aprobada: login, envío/respuesta, presupuesto, recarga de historial, viewport móvil y logout.
- Limitaciones: catálogo y orientación deterministas de prueba; sesiones e historial en memoria; no conectado a identidad de PostgreSQL.
- Cierre 2026-10-02 (America/Lima): 12 pruebas integradas aprobadas; `compileall` sin errores; `pip check` sin incompatibilidades; JavaScript validado.
- Evidencia local regenerable: `.local/quote-example.json`, `.local/acceptance-traces.jsonl`, capturas desktop/mobile. Se excluye de Git por ser salida de ejecución.
- Servidor temporal de pruebas detenido después de validar el navegador.

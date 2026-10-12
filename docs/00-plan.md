# Plan de trabajo

1. Ventas: modelos validados, catálogo de prueba, grafo LangGraph, presupuesto con subtotales y faltantes. Probar antes de avanzar.
2. Trazabilidad: callbacks de LangGraph, identificadores correlacionados, registro JSONL y fallo controlado. Probar exclusión de secretos.
3. Chat: API autenticada, historial privado y portal para enviar y recibir mensajes; integración con orientación y ventas. Probar acceso, aislamiento y respuestas.
4. Ejecutar suite completa y compilación Python; documentar resultados y ejecución local.

No se necesitan servicios de pago. No se ejecutan los scripts SMTP o PostgreSQL durante las pruebas.

## Cierre

- [x] Tarea 1 implementada y validada antes de iniciar tarea 2 (3 pruebas).
- [x] Tarea 2 implementada y validada antes de iniciar tarea 3 (3 pruebas).
- [x] Tarea 3 implementada y validada (6 pruebas y navegador real).
- [x] Suite integrada: 12 pruebas; compilación final sin errores.

Consultar `04-validacion.md` para evidencia y alcance.

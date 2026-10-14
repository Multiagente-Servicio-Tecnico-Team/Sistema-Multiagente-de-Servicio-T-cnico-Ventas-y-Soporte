# Evidencia 21: documentación del patrón jerárquico

## Resultado

Se creó `docs/20-patron-jerarquico.md` con una vista Mermaid del flujo, inventario de supervisores/agentes, herramientas, estado, RAG, ciclos de ventas/soporte, API, configuración, trazas y pruebas existentes. Se añadieron enlaces relativos a los archivos fuente y nueve lugares sugeridos para capturas.

## Corrección del recuperador técnico

Se conservó `test_no_unrelated_documents_are_returned`: el caso era relevante porque detectó una coincidencia espuria. La palabra «consulta» aparecía en la instrucción del caso de RAM («consulta las memorias RAM del catálogo») y bastaba para que una pregunta de horario recuperase el caso. `retriever.py` ahora trata «consulta(s)» y «sobre» como términos genéricos; la FAQ mantiene su recuperador independiente. El test prueba el límite esperado entre conocimiento técnico y preguntas informativas.

## Decisiones documentales

- Se describe a `agents/teams.py` como selector determinista de equipo, no como supervisor LLM autónomo.
- Se explica que el RAG consulta archivos Markdown localmente y que la FAQ posee su propio recuperador lexical.
- Se indica que el almacén vuelve a consultar PostgreSQL para stock/precio y que las cotizaciones emplean `Decimal`.
- Se exponen limitaciones reales: compras no cotiza proveedores, checkpoint en memoria, inventario sin reserva y compatibilidad física no demostrada por los perfiles.
- Se enumeran las pruebas de workflows, grafo, trazabilidad, recuperación, repositorio y API; se advierte cuáles pueden depender de servicios externos. No se afirma que se hayan ejecutado en esta actualización.
- La regresión del RAG técnico conserva y endurece el caso de consulta no relacionada; ejecución unitaria aislada registrada en el progreso del proyecto.

## Validación

Revisión estática de los archivos enlazados y comprobación de `git diff --check`. Sin pruebas ni conexión/escrituras a servicios externos; no eran necesarias para una tarea documental.

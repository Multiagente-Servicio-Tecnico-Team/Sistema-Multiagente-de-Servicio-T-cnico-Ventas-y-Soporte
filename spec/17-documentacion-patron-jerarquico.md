# Especificación 17: documentación del patrón jerárquico

## Objetivo

Documentar la arquitectura jerárquica ya implementada para facilitar su presentación con capturas y permitir navegar desde la explicación hasta los archivos fuente.

## Contenido requerido

- Identificar supervisor principal y supervisores secundarios, distinguiendo sus responsabilidades reales.
- Inventariar los agentes especializados y las transiciones del grafo LangGraph.
- Explicar el estado compartido, las herramientas de acceso a datos, el cálculo de cotizaciones y el RAG Markdown.
- Relacionar API, configuración de Groq/LangSmith y trazabilidad local.
- Añadir diagrama y espacios sugeridos para capturas.
- Enumerar las pruebas existentes y enlazar los archivos de `tests/`, distinguiendo las aisladas de las que pueden requerir servicios.
- Registrar limitaciones técnicas observadas sin presentar capacidades futuras como implementadas.

## Evidencia

La guía está en [docs/20-patron-jerarquico.md](../docs/20-patron-jerarquico.md). Sus afirmaciones se vinculan a archivos del repositorio y separan recuperación RAG, catálogo actual, persistencia y responsabilidades de agentes. La sección de pruebas lista los archivos existentes y aclara que no fueron ejecutados en esta tarea documental.

## Validación

Revisión estática de referencias y contenido contra `builder.py`, `routing.py`, `state.py`, nodos jerárquicos, herramientas, recuperadores, API y archivos de `tests/`. No se ejecutaron pruebas porque esta tarea solo añade documentación.

# Sistema-Multiagente-de-Servicio-Técnico-Ventas-y-Soporte

## Prueba local

1. Instala dependencias con `pip install -r requirements.txt`.
2. Completa `.env` con `GROQ_API_KEY`, `LANGSMITH_API_KEY` y `DATABASE_URL`.
3. Ejecuta `streamlit run app/web.py` e ingresa el email de un usuario activo.
4. Ejecuta `python -m unittest discover -s tests` para las pruebas locales.

El chat se conserva solo en memoria durante la sesión. El agente técnico recupera
fallas, soluciones y componentes desde `app/agents/orquestador/knowledge/*.md`; agrega allí
secciones Markdown para ampliar el catálogo. El catálogo usa nombres exactos de
repuestos activos de `spare_parts`; la validación de compatibilidad, existencias
y precios se hace en PostgreSQL durante cada consulta. Antes de guardar un ticket,
el agente presenta el resumen y espera confirmación explícita. Los importes se
expresan en soles peruanos (`PEN`, `S/`).

## Estructura del orquestador

```text
app/agents/orquestador/
	agentes/    Nodos de atención, soporte, almacén, ventas y persistencia
	graph/      Estado compartido y supervisor LangGraph
	knowledge/  Recuperador BM25 y catálogo Markdown
	tools/      Herramientas conectadas a PostgreSQL
```

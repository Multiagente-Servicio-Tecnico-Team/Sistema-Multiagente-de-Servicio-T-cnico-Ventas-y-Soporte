# Sistema-Multiagente-de-Servicio-Técnico-Ventas-y-Soporte

## Prueba local

1. Instala dependencias con `pip install -r requirements.txt`.
2. Completa `.env` con `GROQ_API_KEY`, `LANGSMITH_API_KEY` y `DATABASE_URL`.
3. Ejecuta `python -m app.main` e ingresa el email de un usuario ya registrado.
4. Ejecuta `python -m unittest discover -s tests` para las pruebas locales.

El chat se conserva solo en memoria durante la sesión. El agente técnico recupera
fallas, soluciones y componentes desde `app/agents/knowledge/*.md`; agrega allí
secciones Markdown para ampliar el catálogo. La validación de compatibilidad,
existencias y precios continúa dependiendo de PostgreSQL.

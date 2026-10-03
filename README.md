# Sistema-Multiagente-de-Servicio-Técnico-Ventas-y-Soporte

Agente de ventas LangGraph, trazabilidad local y portal autenticado de orientación.

## Ejecutar el portal (Python 3.12)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-agent.txt
.\.venv\Scripts\python.exe -m app.auth
```

El último comando solicita usuario y contraseña y devuelve un JSON con el hash. Copiarlo como valor de `PORTAL_USERS_JSON`:

```powershell
$env:PORTAL_USERS_JSON = '{"usuario":"SALT:HASH_GENERADO"}'
$env:PORTAL_SECURE_COOKIE = 'false' # Solo localhost HTTP
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir http://127.0.0.1:8000 e iniciar sesión. Enviar «Mi laptop no enciende» o «Quiero un presupuesto de ejemplo». Este último muestra mano de obra S/ 80.00 y repuestos S/ 180.00, total S/ 260.00.

También se pueden cargar variables desde `.env` con `uvicorn --env-file .env` si se instala `python-dotenv` (incluido en `requirements.txt`). Usar hashes, nunca contraseñas en claro, en la configuración de usuarios.

`requirements-agent.txt` instala el módulo nuevo de forma independiente. `requirements.txt` incluye además SMTP y PostgreSQL. Las pruebas nuevas no llaman esos servicios.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
```

La suite cubre presupuestos, faltantes, trazas y fallo controlado, autenticación, aislamiento, respuestas y errores. `pytest.ini` excluye los scripts manuales raíz que conectan a servicios reales.

## Documentación en orden

1. [Plan](docs/00-plan.md)
2. [Ventas](docs/01-ventas.md) · [Especificación](spec/01-ventas.md)
3. [Trazabilidad](docs/02-trazabilidad.md) · [Especificación](spec/02-trazabilidad.md)
4. [Chat](docs/03-chat.md) · [Especificación](spec/03-chat.md)
5. [Memoria](memory.md)

Catálogo y orientación de demostración. Sesiones e historial en memoria, con una sola instancia. Las trazas JSONL guardan solo metadatos en `.local/traces.jsonl`.

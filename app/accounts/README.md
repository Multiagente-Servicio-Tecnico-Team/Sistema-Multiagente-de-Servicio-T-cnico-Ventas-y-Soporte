# API de cuentas — registro e inicio de sesión

Servicio Python que registra clientes en la tabla `users` de PostgreSQL con la contraseña protegida por hash
bcrypt y abre sesión con una cookie firmada. Lo usa el frontend (`landing/`) para las pantallas de registro e
inicio de sesión.

## Frameworks y librerías

| Uso | Herramienta |
| --- | --- |
| API HTTP | FastAPI 0.142 + Uvicorn 0.54 |
| Acceso a datos | SQLAlchemy 2.1 con el driver `pg8000` (Python puro, sin compilación) |
| Base de datos | PostgreSQL 16 (esquema del script `creacion_tablas_sin_inserciones.sql`) |
| Hash de contraseñas | bcrypt (costo 12, formato `$2b$12$…`) |
| Validación | Pydantic 2 |
| Pruebas | pytest + TestClient (SQLite en memoria); colección de Postman ejecutable con Newman |

Dependencias en [`requirements-auth.txt`](../../requirements-auth.txt).

## Estructura

```text
app/accounts/
├── api.py        # Aplicación FastAPI: rutas, CORS, cookie de sesión y manejo de errores
├── config.py     # Configuración leída de variables de entorno
├── models.py     # Mapeo de la tabla users (no crea tablas en PostgreSQL)
├── schemas.py    # Validación de los cuerpos de /registro y /login
├── security.py   # bcrypt, firma de la cookie y límite de intentos fallidos
└── service.py    # Reglas de registro y autenticación
tests/test_accounts_api.py                     # Pruebas automáticas
postman/techfix-auth.postman_collection.json   # Pruebas de API con Postman
```

## Rutas

| Método y ruta | Cuerpo | Respuestas |
| --- | --- | --- |
| `POST /registro` | `{ nombre, apellido?, email, telefono, password }` | `201 { usuario }` · `409` correo ya registrado · `422` datos inválidos |
| `POST /login` | `{ email, password }` | `200 { usuario }` + cookie `techfix_session` · `401` credenciales · `429` demasiados intentos |
| `POST /logout` | — | `204` y borra la cookie |
| `GET /me` | — | `200 { usuario }` con sesión válida · `401` sin sesión |
| `GET /salud` | — | `200 { estado, bd }` |

`usuario` = `{ id, nombre, apellido, email, rol }`. El rol viene de la columna `role` (`CUSTOMER`,
`TECHNICIAN`, `ADMIN`); el registro público siempre crea `CUSTOMER`.

## Reglas principales

- Correo en minúsculas y único sin distinguir mayúsculas; teléfono en formato E.164 (`+51987654321`).
- Contraseña de 8 a 72 bytes con mayúscula, número y símbolo. Solo se guarda `password_hash`.
- Si `apellido` no se envía, `nombre` se separa en la primera palabra (nombre) y el resto (apellido).
- El inicio de sesión responde igual para correo inexistente, contraseña incorrecta o cuenta inactiva, y
  siempre verifica un hash para no revelar qué correos existen por el tiempo de respuesta.
- 5 intentos fallidos del mismo correo en 15 minutos bloquean temporalmente el acceso (429).
- Los errores 422 indican el campo pero no repiten los valores enviados.
- Cookie de sesión `HttpOnly`, `SameSite=Lax`, firmada con HMAC-SHA256 y válida 8 horas.

## Ejecución local

1. Crear la base de datos y aplicar el script del equipo:

   ```bash
   createdb -U postgres techfix
   psql -U postgres -d techfix -f creacion_tablas_sin_inserciones.sql
   ```

2. Instalar dependencias (Python 3.12):

   ```bash
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements-auth.txt
   ```

3. Configurar `.env` en la raíz del repositorio (ver `.env.example`):

   ```bash
   DATABASE_URL=postgresql+pg8000://postgres:CLAVE@localhost:5432/techfix
   AUTH_SECRET=<cadena aleatoria de 32 caracteres o más>
   AUTH_SECURE_COOKIE=false
   FRONTEND_ORIGINS=http://localhost:5173
   ```

   `AUTH_SECRET` se puede generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

4. Iniciar la API:

   ```bash
   .venv/Scripts/python -m uvicorn app.accounts.api:create_app --factory --host localhost --port 8000
   ```

5. Conectar el frontend con `VITE_API_URL=http://localhost:8000` en `landing/.env` y ejecutar
   `npm --prefix landing run dev`.

Usar `localhost` (no `127.0.0.1`) tanto en la API como en el frontend: así el navegador trata ambos puertos como
el mismo sitio y envía la cookie de sesión.

## Pruebas

Automáticas, sin PostgreSQL:

```bash
.venv/Scripts/python -m pytest tests/test_accounts_api.py -q
```

API con Postman: importar `postman/techfix-auth.postman_collection.json` y ejecutar la colección completa en
orden (la primera petición genera un correo único). También desde la terminal con Newman:

```bash
npx newman run postman/techfix-auth.postman_collection.json
```

Verificación en la base de datos:

```sql
SELECT id, email, phone, password_hash, name, last_name, role, active FROM users ORDER BY id;
```

## Despliegue

- Definir `DATABASE_URL` hacia la base de datos en la nube, un `AUTH_SECRET` propio y
  `FRONTEND_ORIGINS` con la URL pública del frontend.
- Servir con HTTPS y dejar `AUTH_SECURE_COOKIE=true` (valor por defecto).
- Ejecutar detrás de un proxy o con varios procesos de Uvicorn; el límite de intentos fallidos vive en la
  memoria de cada proceso.

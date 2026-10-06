# Progreso de implementacion

## Etapa 1: configuracion y dependencias
- [x] Declarar LangGraph, LangChain/Groq y variables de LangSmith.
- [x] Crear `.env` local con valores vacios de secretos y cadena PostgreSQL pendiente.
- [x] Mantener `.env` fuera del control de versiones.
- Commit de etapa 1: ____________________________________

## Etapa 2: persistencia y acceso de prueba
- [x] Resolver usuarios por email existente sin cargar columnas sensibles adicionales.
- [x] Persistir tickets y presupuestos; las conversaciones no se guardan.
- [x] Crear tablas de presupuestos si no existen.
- [x] Mantener mensajes solo en el checkpointer en memoria durante la sesion.
- Commit de etapa 2: ____________________________________

## Etapa 3: agentes y orquestacion
- [x] Implementar atencion, soporte tecnico, almacen y ventas como nodos.
- [x] Incorporar supervisor LangGraph, aclaraciones multiturno y trazabilidad LangSmith por variables de entorno.
- [x] Recuperar soluciones y componentes relevantes desde catalogos Markdown con BM25 local.
- [x] Calcular importes en codigo para no delegar aritmetica al LLM.
- Commit de etapa 3: ____________________________________

## Etapa 4: ejecucion y verificacion local
- [x] Solicitar email como identidad de prueba y exigir que el usuario exista en la BD.
- [x] Agregar pruebas unitarias de calculo del presupuesto.
- [x] Agregar pruebas de recuperacion Markdown, normalizacion de tildes y consultas sin coincidencias.
- [ ] Ejecutar el CLI integrado contra PostgreSQL y Groq.
- Commit de etapa 4: ____________________________________

## Pendiente de credenciales
- [ ] Probar conexiones con Groq, LangSmith y PostgreSQL cuando se agreguen las claves.

## Ejecucion
- Instalar dependencias: `pip install -r requirements.txt`.
- Completar `.env` con claves y `DATABASE_URL` real.
- Iniciar: `python -m app.main`.
- Pruebas sin servicios externos: `python -m unittest discover -s tests`.

## Supuestos pendientes de confirmar
- La tabla `usuarios` tiene `id` o `usuario_id`, `email` y opcionalmente `nombre`.
- El inventario usa la tabla `repuestos` (o `repuesto`) con nombre, stock/cantidad y precio.
- La tabla `tickets` debe tener columnas compatibles con el identificador del usuario, tipo y estado.
- Las tablas de conversaciones creadas por versiones anteriores no se eliminan ni se modifican; esta version deja de escribir en ellas.
- El catalogo RAG se administra en `app/agents/knowledge/`; la recuperacion es local por ranking BM25.
- La moneda predeterminada es COP y se cambia con `CURRENCY`.
- LangSmith traza el estado del grafo; se omiten email y nombre, pero el identificador interno del usuario forma parte del estado para persistir el presupuesto.
- La validacion real de conexiones queda pendiente de credenciales y acceso a PostgreSQL.
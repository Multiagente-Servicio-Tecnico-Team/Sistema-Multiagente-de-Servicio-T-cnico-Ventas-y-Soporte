# Progreso de implementacion

## Etapa 1: configuracion y dependencias
- [x] Declarar LangGraph, LangChain/Groq y variables de LangSmith.
- [x] Crear plantilla y `.env` local ignorado por Git para secretos y conexion PostgreSQL.
- [x] Mantener `.env` fuera del control de versiones.
- Commit de etapa 1: ____________________________________

## Etapa 2: persistencia y acceso de prueba
- [x] Resolver usuarios por email existente sin cargar columnas sensibles adicionales.
- [x] Persistir tickets y presupuestos; las conversaciones no se guardan.
- [x] Usar las tablas existentes `quotes` y `quote_details` sin crear tablas paralelas.
- [x] Mantener mensajes solo en el checkpointer en memoria durante la sesion.
- [x] Mapear el repositorio al esquema PostgreSQL existente sin crear tablas paralelas.
- [x] Guardar diagnostico provisional y cambiar estado del ticket al cotizar.
- [x] Mostrar diagnÃ³stico y presupuesto sugerido antes de pedir confirmacion.
- [x] Guardar ticket y presupuesto en una sola transaccion despues del "si" explicito.
- Commit de etapa 2: ____________________________________

## Etapa 3: agentes y orquestacion
- [x] Reorganizar agentes, herramientas, conocimiento y supervisor en `app/agents/orquestador/`.
- [x] Implementar los nueve agentes: atenciÃ³n/triage, ventas, soporte HW, soporte SW, almacÃ©n, compras, pagos, logÃ­stica y garantÃ­a.
- [x] Incorporar grafo LangGraph con estado por `thread_id`; ChatGroq atiende triage, FAQ y diagnÃ³stico; LangSmith usa variables de entorno.
- [x] AÃ±adir RAG Markdown local para fallas tÃ©cnicas y preguntas frecuentes con ranking lÃ©xico y normalizaciÃ³n de tildes.
- [x] Calcular importes con `Decimal`; precios y existencias provienen de PostgreSQL.
- [x] AÃ±adir consulta de inventario, Ã³rdenes pendientes, registros logÃ­sticos y emisiÃ³n/consulta de garantÃ­as.
- [x] Copiar los prompts fuente de los nueve agentes como Markdown en `knowledge/`.
- [x] Registrar reclamos de garantÃ­a sÃ³lo con pÃ³liza vigente, ticket del cliente y motivo; inserciÃ³n y cambio de estado atÃ³micos.
- [ ] Completar validaciÃ³n exhaustiva de compatibilidad PC y precio externo cuando exista informaciÃ³n verificable.
- Commit de etapa 3: ____________________________________

## Etapa 4: ejecucion y verificacion local
- [x] Solicitar email como identidad de prueba y exigir que el usuario exista en la BD.
- [x] Agregar pruebas unitarias de calculo del presupuesto.
- [x] Agregar pruebas de recuperacion Markdown, normalizacion de tildes y consultas sin coincidencias.
- [x] Crear interfaz web provisional con verificacion por email.
- [x] Ejecutar pruebas unitarias seguras del paquete: `15 passed, 10 subtests passed`.
- [ ] Verificar flujo integral PostgreSQL/Groq/LangSmith; la salida de red está bloqueada en esta ejecución.
- Commit de etapa 4: ____________________________________

## Verificacion de integraciones
- [ ] Verificar autenticaciÃ³n Groq, LangSmith y PostgreSQL desde esta ejecuciÃ³n.

## Ejecucion
- Instalar dependencias: `pip install -r requirements.txt`.
- Configurar claves Groq/LangSmith y `DATABASE_URL` en `.env`.
- Iniciar interfaz: `streamlit run app/web.py`.
- Pruebas sin servicios externos: `python -m unittest discover -s tests`.

## Esquema confirmado
- La tabla `users` autentica por `email` y solo admite cuentas con `active = true`.
- El inventario es `spare_parts`; usa `name`, `current_stock`, `unit_price` y `active`.
- Los tickets se guardan en `tickets` con `customer_id`, `code`, `title`, `failure_description` y `provisional_diagnosis`.
- Los presupuestos se guardan en `quotes` y `quote_details`; los tickets pasan a `IN_DIAGNOSIS` y `QUOTED`.
- Las tablas de conversaciones creadas por versiones anteriores no se eliminan ni se modifican; esta version deja de escribir en ellas.
- El catÃ¡logo RAG se administra en `app/agents/orquestador/knowledge/`; la recuperaciÃ³n es local por ranking lÃ©xico.
- La moneda configurada es PEN y se presenta como `S/`.
- LangSmith traza el estado del grafo; se omiten email y nombre, pero el identificador interno del usuario forma parte del estado para persistir el presupuesto.
- El Ã¡rbol `app/agents` estaba vacÃ­o; el paquete se creÃ³ en la ruta esperada.
- Los perfiles y SQL adjuntos se leyeron desde Downloads. DirecciÃ³n y horarios FAQ son datos ficticios de demo y requieren confirmaciÃ³n antes de producciÃ³n.
- El esquema de referencia no incluye costo ni relaciÃ³n proveedor-producto; compras no inventa costos externos.
- Los estados iniciales reflejan el esquema (`NEW`, `IN_DIAGNOSIS`, `QUOTED`, `PAYMENT_PENDING`, `PENDING_RECEIPT`, `IN_REVIEW`). La orden de pago requiere total positivo; una venta de total cero no puede generar pago en el enum/esquema actual.
- Pruebas seguras ejecutadas: `tests/test_confirmation.py`, `tests/test_graph_confirmation.py`, `tests/test_quotes.py`, `tests/test_knowledge_base.py`; `compileall` completado.
- `test_database.py` asume la tabla `usuarios` y `test_email.py` envÃ­a correo al importarse; se excluyeron de la corrida segura.

## Actualización 2026-10-13: migración de interfaz a FastAPI
- [x] Reemplazar interfaz Streamlit por API FastAPI con documentación OpenAPI en `/docs`.
- [x] Agregar `GET /health`, identificación por correo en PostgreSQL y chat LangGraph por thread.
- [x] Vincular cada sesión a `user_id` validado para que otro usuario no reutilice el hilo.
- [x] Mantener una instancia del grafo LangGraph en proceso para preservar MemorySaver entre solicitudes.
- [x] Diagnosticar el mensaje `APIConnectionError`: provenía de salida de red a Groq dentro del sandbox, no de la lectura del id. Groq contestó exitosamente fuera del sandbox con la configuración existente.
- [x] Corregir las FAQ: triage explícito para preguntas informativas y recuperación RAG de pago/ubicación con stopwords y sinónimos.
- [x] Prueba E2E: usuario activo admin@servicio.com -> user_id entero -> FastAPI chat -> respuesta FAQ de Groq (HTTP 200).
- [x] Pruebas locales: `20 passed, 10 subtests passed`; `compileall` completado.
- [x] Servidor actual en `http://127.0.0.1:8000`; Swagger UI en `/docs`.
## Actualización 2026-10-13: pantalla inicial de acceso
- [x] La ruta `/` ahora sirve un formulario web de correo en HTML en lugar de JSON.
- [x] Tras identificar un usuario activo, el mismo navegador muestra el chat y llama a los endpoints JSON existentes.
- [x] Prueba de pantalla raíz: contenido HTML, campo email y llamadas a identificación/chat.
- [x] Validación local final: `21 passed, 10 subtests passed`; `compileall` correcto.

## Actualización 2026-10-13: RAG de atención y prompts de agentes
- [x] Consolidar FAQ de tienda, servicios, pagos, despacho y garantía en `knowledge/atencion.md`, basado en `contenido/Patrones.md`; señalar como demo los datos no confirmados de ubicación/horario/precios.
- [x] Enlazar el recuperador FAQ con `atencion.md` y retirar el documento FAQ duplicado; mantener el RAG técnico independiente.
- [x] Incorporar prompts de sistema en las definiciones Python de los nueve agentes; Atención separa triage, FAQ y cierre.
- [x] Corregir codificación UTF-8 en prompts y textos de los agentes; la búsqueda de mojibake en `app/**/*.py` no devuelve coincidencias.
- [x] Evitar que consultas sobre estado/reclamo de garantía se respondan como FAQ general y conservar el enrutamiento del flujo.
- [x] Verificar API, confirmación, grafo, presupuestos y RAG: `26 passed, 10 subtests passed`; `compileall` correcto.


## Actualizaci?n 2026-10-13: Caso 4, venta directa de repuestos y perif?ricos
- [x] Extraer la solicitud expl?cita de RAM SODIMM DDR4 16GB y mouse gamer Logitech como `SALE`, pedir confirmaci?n de alta y crear ticket `NEW` con el cliente autenticado.
- [x] Preservar `request_type`, ticket y art?culos entre turnos de LangGraph; enrutar Ventas -> Almac?n -> Ventas aun cuando el agente espere respuesta del cliente.
- [x] Consultar PostgreSQL y presentar las cuatro alternativas de RAM con stock/precio, m?s el Logitech G203 (S/ 24); permitir selecci?n y cotizar a S/ 72 con mano de obra S/ 0.
- [x] La vista previa ahora pregunta expl?citamente si acepta; s?lo tras aceptaci?n se registran cotizaci?n `DIRECT_SALE`/`ACCEPTED`, detalles, pago `PENDING`, modalidad log?stica y garant?a de tres meses.
- [x] Corregir sintaxis rota del alta de ticket en `customer_service.py`, ruta SALE de `sales_node`, y prioridad del supervisor para el traspaso a Almac?n.
- [x] Prueba E2E del grafo con BD PostgreSQL real (Groq simulado en la corrida final): listado, selecci?n, S/ 72, cotizaci?n id 20, pago pendiente, retiro presencial y p?liza emitida; ticket temporal `TCK-3C1B829023` y sus dependencias se eliminaron. Conteos de BD restaurados: tickets 41, quotes 10, quote_details 11, payments 1, logistics_records 0, warranties 0.
- [x] Validaci?n local: `32 passed, 10 subtests passed`; `compileall` correcto.
- [ ] Groq no qued? verificado de punta a punta: la llamada directa desde esta ejecuci?n devolvi? `APIConnectionError`/`WinError 10013`; la clasificaci?n se simul? en el E2E para aislar el grafo y la base.


## Actualizaci?n 2026-10-14: consulta de precio RAM DDR4 8GB
- [x] Revisar el esquema/datos SQL adjuntos y la conexi?n PostgreSQL: existen RAM DDR4 8GB Kingston desktop a S/ 26.00, Kingston laptop SODIMM 2400/2666/3200 MT/s a S/ 21.60 y otras marcas; los datos est?n en `spare_parts`.
- [x] Diagnosticar la falla: Triage ped?a marca/modelo antes de consultar; el filtro del almac?n eliminaba tokens cortos/atributos y b?squeda SQL limitaba antes del filtro exacto.
- [x] Reconocer preguntas de precio de RAM y consultar inventario inmediatamente sin crear ticket; filtrar por capacidad, generaci?n DDR, marca y formato y s?lo listar stock positivo.
- [x] Respuesta en grafo contra BD real para `quiero una ram 8 gb ddr4 que precio tienen?`: 20 coincidencias listadas con nombre, precio y stock; para `marca kingston para la ram`: 6 Kingston listadas y pregunta laptop/desktop; tras `para laptop`, quedan 3 variantes SODIMM de Kingston.
- [x] No se escribieron tickets ni cotizaciones en esta consulta.
- [x] A?adir cobertura de reconocimiento, filtro de Almac?n y refinamiento de opciones; `35 passed, 10 subtests passed`, `compileall` correcto.


## Actualizaci?n 2026-10-14: continuaci?n de RAM a cotizaci?n y compra
- [x] Corregir el `TypeError` del filtro de formato cuando `category` es `NULL`, normalizando nombre/categor?a con valores vac?os seguros.
- [x] Refinar el flujo: consulta general -> formato (laptop/desktop) -> marca -> velocidad/opci?n -> presupuesto preliminar -> aceptaci?n expl?cita.
- [x] Al aceptar una cotizaci?n iniciada desde una consulta de precio, crear el ticket `SALE` y registrar cotizaci?n `DIRECT_SALE` aceptada; continuar con pago `PENDING`, modalidad log?stica y p?liza. Si rechaza antes, no crear ticket/cotizaci?n.
- [x] E2E con PostgreSQL: laptop Kingston SODIMM 3200 MT/s, S/ 21.60, ticket/cotizaci?n/pago/log?stica/garant?a; registros de prueba eliminados y conteos previos restaurados.
- [x] Agregar pruebas para `category=NULL`, selecci?n de producto y ticket/cotizaci?n al aceptar; validaci?n: `38 passed, 10 subtests passed`, `compileall` correcto.

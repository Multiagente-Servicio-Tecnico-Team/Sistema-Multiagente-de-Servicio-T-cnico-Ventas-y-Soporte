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
- [x] Mostrar diagnóstico y presupuesto sugerido antes de pedir confirmacion.
- [x] Guardar ticket y presupuesto en una sola transaccion despues del "si" explicito.
- Commit de etapa 2: ____________________________________

## Etapa 3: agentes y orquestacion
- [x] Reorganizar agentes, herramientas, conocimiento y supervisor en `app/agents/orquestador/`.
- [x] Implementar atencion, soporte tecnico, almacen y ventas como nodos.
- [x] Incorporar supervisor LangGraph, aclaraciones multiturno y trazabilidad LangSmith por variables de entorno.
- [x] Recuperar soluciones y componentes relevantes desde catalogos Markdown con BM25 local.
- [x] Calcular importes en codigo para no delegar aritmetica al LLM.
- [x] Sincronizar nombres de componentes del catalogo Markdown con `spare_parts`.
- Commit de etapa 3: ____________________________________

## Etapa 4: ejecucion y verificacion local
- [x] Solicitar email como identidad de prueba y exigir que el usuario exista en la BD.
- [x] Agregar pruebas unitarias de calculo del presupuesto.
- [x] Agregar pruebas de recuperacion Markdown, normalizacion de tildes y consultas sin coincidencias.
- [x] Crear interfaz web provisional con verificacion por email.
- [x] Probar el flujo multiturno en español: vista previa sin escritura y persistencia tras confirmar.
- Commit de etapa 4: ____________________________________

## Verificacion de integraciones
- [x] Verificar autenticacion y acceso a modelos de Groq.
- [x] Verificar acceso a proyectos de LangSmith.
- [x] Verificar PostgreSQL e inspeccionar tablas/columnas sin leer datos de usuarios.

## Patron jerarquico — ventas (checkpoint de commit pendiente)
- [x] Implementar la ruta comercial y subagentes para FAQ, ventas, pagos, garantía, soporte HW/SW, almacén, compras y logística.
- [x] Añadir consultas de catálogo y garantía parametrizadas; no se permite SQL generado por LLM.
- [x] Crear tickets `NEW` durante el triage de ventas y servicio; actualizar el mismo ticket con diagnóstico y estado `IN_DIAGNOSIS`.
- [x] Registrar cotización `ACCEPTED`, pago `PENDING` y estado final `PAYMENT_PENDING` en una transacción tras aceptación explícita; cancelar el ticket si se rechaza.
- [x] Alinear persistencia del diagnóstico con `hardware_diagnosis` y `software_diagnosis`, y la tarifa predeterminada de mantenimiento con S/ 35.00 del prompt.
- [x] Verificar que la BD local contiene las tres columnas de diagnóstico; no se hicieron escrituras reales.
- [x] Ejecutar suite aislada ampliada tras corregir el ciclo de tickets de servicio: 60 pruebas aprobadas.
- Limitaciones reales: el esquema no define compatibilidad de PC ni ofertas relacionadas con proveedores; no se reserva stock ni se afirma pago/entrega completados.
- Commit del usuario: ____________________

## Patron jerarquico — trazabilidad (checkpoint de commit pendiente)
- [x] Correlacionar nodos y herramientas por UUID aleatorio de ejecución.
- [x] Registrar solo timestamp, identificador de ejecución, componente, tipo y evento; excluir mensajes, identidad, entradas/resultados y texto de excepciones.
- [x] Probar eventos exitosos y de error, correlación y ausencia de datos privados.
- Limitación: JSONL local por proceso; despliegue horizontal requiere un backend compartido y política de retención.
- Commit del usuario: ____________________

## Chat autenticado — corregido al final; smoke test de despliegue pendiente
- [x] Corregir bases de URL de producción para login y chat: ambas usan rutas same-origin `/backend/*`, incluso si la build recibe una URL absoluta.
- [x] Confirmar `credentials: include` en login/chat con pruebas de contrato existentes; nuevas pruebas validan rutas same-origin de producción.
- [x] Vitest: 61 pruebas aprobadas; build Vite exitoso y `dist/_redirects` presente.
- [ ] Tras publicar, confirmar en dominio Netlify real `Set-Cookie` y el envío de `Cookie` en `POST /backend/api/chat`; no se realizó deploy en esta sesión.
- Commit del usuario: ____________________

## Ejecucion
- Instalar dependencias: `pip install -r requirements.txt`.
- Configurar claves Groq/LangSmith y `DATABASE_URL` en `.env`.
- Iniciar interfaz: `streamlit run app/web.py`.
- Pruebas sin servicios externos: `python -m unittest discover -s tests`.

## Esquema confirmado
- La tabla `users` autentica por `email` y solo admite cuentas con `active = true`.
- El inventario es `spare_parts`; usa `name`, `current_stock`, `unit_price` y `active`.
- Los tickets usan `customer_id`, `code`, `title`, `failure_description`, `diagnosis_type`, `hardware_diagnosis` y `software_diagnosis`; el antiguo `provisional_diagnosis` no es requisito del esquema vigente.
- Los presupuestos se guardan en `quotes` y `quote_details`; el flujo jerárquico crea el ticket en `NEW`, lo actualiza a `IN_DIAGNOSIS` al guardar el diagnóstico y concluye en `PAYMENT_PENDING` al aceptar una cotización y registrar el pago `PENDING`.
- Las tablas de conversaciones creadas por versiones anteriores no se eliminan ni se modifican; esta version deja de escribir en ellas.
- El catalogo RAG se administra en `app/agents/orquestador/knowledge/`; la recuperacion es local por ranking BM25.
- La moneda configurada es PEN y se presenta como `S/`.
- LangSmith traza el estado del grafo; se omiten email y nombre, pero el identificador interno del usuario forma parte del estado para persistir el presupuesto.
- Las credenciales presentes en `.env` autenticaron correctamente contra Groq y LangSmith; PostgreSQL acepto lectura y escrituras de prueba.
- El servidor Streamlit local responde en `http://localhost:8501`.
# Diseño del sistema multiagente

## Objetivo y alcance

Implementar el flujo descrito en `info.md` como una aplicación Python con LangGraph,
Groq, PostgreSQL, LangSmith y una interfaz web de chat para pruebas. `info.md` está
ignorado por la configuración local existente de Git; este documento registra el
diseño sin cambiar esa configuración ni modificar ese archivo.

El prototipo:

- Identifica al cliente por el email que ya existe en `users`, solo si el usuario
  está activo y su rol es `CUSTOMER`. No registra usuarios nuevos.
- Conserva el estado conversacional solo durante la sesión del navegador; no agrega
  una tabla para almacenar conversaciones.
- Consulta `spare_parts` para obtener existencias y precios reales.
- Abre el ticket en `IN_DIAGNOSIS`; guarda `quotes` y `quote_details` y cambia el
  ticket a `QUOTED` en una única transacción cuando el inventario está confirmado.
- No permite al modelo generar SQL ni decidir precios finales.

## Patrón jerárquico en LangGraph

El grafo implementa un supervisor de atención que controla el flujo y deriva el
trabajo a agentes especializados. Las transiciones, las validaciones y las
operaciones de base de datos se definen en código; el LLM no puede saltarse pasos.

```text
START
  -> atención (supervisor: clasifica intención, extrae datos y decide si falta
     aclaración)
       -> END, si necesita preguntar al cliente
       -> soporte técnico, si hay información suficiente para una reparación
            -> abrir ticket en estado IN_DIAGNOSIS
                 -> almacén/logística (consulta parametrizada de inventario)
                      -> ventas (calcula importes con precios de PostgreSQL)
                           -> persistencia transaccional de cotización y cambio a
                              estado QUOTED
                                -> atención (presenta el resultado)
                                     -> END
                      -> END, si falta stock o hay productos ambiguos
       -> atención, para consultas informativas que no requieren cotización
            -> END
```

### Responsabilidad y límites de cada agente

| Agente | Responsabilidad | Límite |
| --- | --- | --- |
| Atención / supervisor | Mantiene el diálogo, identifica la intención, solicita los datos que falten y presenta el resultado. | No diagnostica, cotiza ni escribe SQL. |
| Soporte técnico | Propone diagnóstico provisional, horas de trabajo y repuestos por nombre/código. | No inventa existencias ni precios; su salida es estructurada y validada. |
| Almacén y logística | Busca repuestos activos en `spare_parts` y lee precio y stock. | Solo SELECT parametrizados; los artículos sin stock se informan, no se cotizan. |
| Ventas | Calcula mano de obra, subtotales y total usando valores validados del almacén. | La tarifa de mano de obra es configuración del servidor; nunca la fija el LLM. |

El grafo conserva `messages` y los datos de trabajo estructurados en el estado de
LangGraph. Para la primera versión se utiliza memoria de proceso ligada a un
`thread_id` de sesión del navegador: reiniciar el servidor descarta esas sesiones.

## Persistencia basada en el esquema de `info.md`

1. Buscar `users` por email, `active = TRUE` y `role = 'CUSTOMER'`. Si no existe,
   solicitar que el cliente use un email registrado; no crear ni modificar usuarios.
2. Consultar repuestos activos por `code` o coincidencia acotada de nombre, usando
   parámetros enlazados. Nunca ejecutar SQL generado por el modelo.
3. Tras el diagnóstico, insertar `tickets` con el `request_type` detectado,
   `status = 'IN_DIAGNOSIS'` y el diagnóstico provisional.
4. Si algún repuesto no existe, es ambiguo o no tiene stock suficiente, conservar
   el ticket en análisis, explicar el motivo y no crear una cotización parcial.
5. Si el inventario está confirmado, calcular mano de obra y repuestos en servidor;
   insertar `quotes` con `status = 'PENDING'` y actualizar el ticket a `QUOTED`.
6. Insertar en `quote_details` solo repuestos confirmados, con precio leído y
   subtotal calculado; guardar la cotización, detalles y cambio de estado en una
   única transacción.
7. Un error debe revertir la transacción de cotización y mostrarse como error, no
   como una cotización guardada.

No se crean registros de conversación ni se alteran ENUMs/tablas en este alcance.
El `technician_id` es nullable según el esquema y queda vacío mientras no haya un
usuario técnico asignado.

## Componentes de aplicación

- **API/UI:** FastAPI sirve una página estática de chat y un endpoint JSON para
  enviar mensajes. La respuesta incluye texto, estado de la interacción y, cuando
  corresponda, referencia del ticket/cotización.
- **Orquestación:** `StateGraph` de LangGraph con nodos explícitos y ruteo
  condicional, modelo Groq configurable y salidas estructuradas validadas.
- **Base de datos:** SQLAlchemy y el driver PostgreSQL ya disponible en el proyecto;
  la URL se configura mediante `DATABASE_URL`. Las consultas existentes usan
  nombres del esquema de `info.md` (`users`, `tickets`, no `usuarios` ni `codigo`).
- **Observabilidad:** integración automática LangChain/LangGraph con LangSmith.
  Configurar proyecto y tracing por variables de entorno. No incluir emails,
  teléfonos, hashes, secretos ni texto identificable en metadata; habilitar
  ocultación de entradas/salidas para traces que puedan contener datos personales.
- **Configuración:** claves únicamente en `.env` local o secretos del entorno:
  `GROQ_API_KEY`, `GROQ_MODEL`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`,
  `LANGSMITH_PROJECT`, `DATABASE_URL` y tarifa de mano de obra.

## API y experiencia mínima de prueba

- `GET /` muestra el chat y un campo separado para el email del cliente registrado.
- `POST /api/chat` recibe `session_id`, `email` y `message`; devuelve respuesta,
  estado y datos de cotización/ticket si se guardaron.
- Validar tamaño/formato de entrada, rechazar campos vacíos y usar un UUID opaco
  para la sesión. No usar email, nombre ni mensaje en el `thread_id` de LangGraph.
- Mostrar preguntas de aclaración y errores de configuración/DB de forma explícita.
  La UI nunca debe mostrar que se creó un ticket si la transacción falló.

## Validación por bloques

1. **Diseño y registro:** documentar la arquitectura y decisiones acordadas.
2. **Fundación:** dependencias, carga segura de configuración y acceso a PostgreSQL.
3. **Grafo y agentes:** flujo jerárquico, herramientas seguras, persistencia y tests
   unitarios con dependencias externas simuladas.
4. **Chat de prueba:** endpoints, sesión en memoria, UI mínima y validación final.

Cada bloque termina con un checkpoint para que el usuario revise y haga commit antes
de iniciar el siguiente. No se deben incluir ni revertir cambios previos del usuario.

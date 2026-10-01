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
            -> recuperación lexical RAG (guías sintéticas locales)
                 -> soporte técnico (diagnóstico provisional y horas)
                      -> almacén/logística (consulta parametrizada de inventario)
                           -> ventas (cálculo con tarifa y precios PostgreSQL)
                                -> atención presenta propuesta indicativa
                                     -> END, sin escrituras antes de confirmar
            -> atención, al recibir confirmación
                 -> almacén/logística (revalida precio y stock)
                      -> ventas (recalcula)
                           -> atención pide confirmar de nuevo si algo cambió
                           -> persistencia atómica de ticket, cotización y detalles
                                -> END
                 -> END, si se rechaza o falta stock/producto
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
| Recuperación de conocimiento | Recupera casos sintéticos en español por coincidencia lexical. | No usa embeddings; rangos UM son demostrativos y no entran al cálculo comercial. |

El grafo conserva `messages` y los datos de trabajo estructurados en el estado de
LangGraph. Para la primera versión se utiliza memoria de proceso ligada a un
`thread_id` de sesión del navegador: reiniciar el servidor descarta esas sesiones.

## Persistencia basada en el esquema de `info.md`

La base PostgreSQL de desarrollo ya fue migrada en el sitio desde sus nombres
españoles al esquema inglés de `info.md`; el script auditable es
[`../sql/migrate_spanish_schema_to_english.sql`](../sql/migrate_spanish_schema_to_english.sql).
La conversión renombra tablas, columnas, tipos y valores ENUM, y secuencias de
identidad, sin copiar ni eliminar filas. No debe repetirse en una base ya migrada.

1. Buscar `users` por email, `active = TRUE` y `role = 'CUSTOMER'`. Si no existe,
   solicitar que el cliente use un email registrado; no crear ni modificar usuarios.
2. Consultar repuestos activos por `code` o coincidencia acotada de nombre, usando
   parámetros enlazados. Nunca ejecutar SQL generado por el modelo.
3. Recuperar guías RAG simuladas pertinentes. Las guías pueden sugerir causas,
   repuestos y horas, pero no prueban una falla ni definen precios reales.
4. Consultar inventario activo por código/nombre usando parámetros enlazados. Si
   no existe un resultado único o falta stock, informar y no escribir ticket ni
   cotización.
5. Presentar al cliente diagnóstico y cálculo indicativos, diferenciando horas
   estimadas, precio real de inventario y material RAG simulado. No persistir aún.
6. Solo tras una respuesta afirmativa inequívoca, revalidar stock y precio. Si
   cambió cualquiera de esos valores, recalcular y pedir una nueva confirmación.
7. Con datos todavía válidos, crear `tickets` en `IN_DIAGNOSIS`, `quotes` en
   `PENDING`, `quote_details` y el estado `QUOTED` del ticket dentro de una sola
   transacción. Un error revierte todo.
8. Una respuesta negativa cancela la propuesta sin insertar registros.

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
- La cotización indicativa aparece en el chat antes de persistir y el cliente debe
  confirmar explícitamente; la respuesta incluye cifras estructuradas en la API.

## Validación por bloques

1. **Diseño y registro:** documentar la arquitectura y decisiones acordadas.
2. **Fundación:** dependencias, carga segura de configuración y acceso a PostgreSQL.
3. **Grafo y agentes:** flujo jerárquico, herramientas seguras, persistencia y tests
   unitarios con dependencias externas simuladas.
4. **Chat de prueba:** endpoints, sesión en memoria, UI mínima y validación final.

Cada bloque termina con un checkpoint para que el usuario revise y haga commit antes
de iniciar el siguiente. No se deben incluir ni revertir cambios previos del usuario.

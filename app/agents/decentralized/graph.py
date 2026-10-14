import json
from app.agents.decentralized.garantia import garantia_node, garantia_tools
from app.agents.decentralized.warranty_operations import validate_pending_warranty_operation
from app.agents.decentralized.policy import handoff

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.policy import repuesto_confirmado, software_comercial_elegible
from app.agents.decentralized.policy import inventario_vigente, preparar_inventario
from app.agents.decentralized.policy import evaluar_abastecimiento
from app.agents.decentralized.handoffs import (
    HANDOFF_TOOLS, handoff_reason, validate_handoff, make_handoff_record, selected_handoff,
)
from app.agents.decentralized.soporte import soporte_node, soporte_tools
from app.agents.decentralized.tecnico import tecnico_node, tecnico_tools
from app.agents.decentralized.ventas import ventas_node, ventas_tools
from app.agents.decentralized.almacen import almacen_node, almacen_tools
from app.agents.decentralized.software import software_node, software_tools
from app.agents.decentralized.compras import compras_node, compras_tools
from app.agents.decentralized.facturacion import facturacion_node, facturacion_tools
from app.agents.decentralized.logistica import logistica_node, logistica_tools
from app.agents.decentralized.logistics_operations import validate_pending_logistics_operation
from app.agents.decentralized.payment_operations import validate_pending_payment_operation
from langgraph.runtime import Runtime
from typing_extensions import TypedDict


class FinancialContext(TypedDict, total=False):
    authenticated_customer_id: int

MAX_HANDOFFS = 5
MAX_TOOL_ITERATIONS = 6

AGENT_NODES = {
    "soporte": soporte_node, "tecnico": tecnico_node,
    "ventas": ventas_node, "almacen": almacen_node,
    "software": software_node,
    "compras": compras_node,
    "facturacion": facturacion_node,
    "logistica": logistica_node,
    "garantia": garantia_node,
}


def detectar_handoff(messages):
    """Identifica la primera transferencia exitosa del lote final."""
    result = selected_handoff(messages)
    return HANDOFF_TOOLS[result.name] if result is not None else None


def extraer_repuesto_handoff(messages):
    """Valida los datos estructurados de transferir_a_almacen."""
    for mensaje in [selected_handoff(messages)]:
        if mensaje is None or mensaje.name != "transferir_a_almacen":
            return None
        if mensaje.status == "error":
            return None
        try:
            datos = json.loads(mensaje.content)
        except (ValueError, TypeError):
            return None
        if not isinstance(datos, dict):
            return None
        if datos.get("accion") != "TRANSFERIR_ALMACEN":
            return None
        nombre = datos.get("nombre_repuesto")
        cantidad = datos.get("cantidad")
        if not isinstance(nombre, str) or not nombre.strip():
            return None
        if type(cantidad) is not int or cantidad <= 0:
            return None
        return {"name": nombre.strip(), "quantity": cantidad}
    return None


def registrar_handoff(state: AgentState, origen: str):
    """Audita herramientas y transferencias entre agentes."""
    destino = detectar_handoff(state["messages"])
    motivo = handoff_reason(state["messages"]) if destino else None
    # Almacén entrega datos verificados a Ventas en la misma ejecución.
    lote = []
    for message in reversed(state["messages"]):
        if not isinstance(message, ToolMessage):
            break
        lote.append(message)
    inventario_actual = any(
        message.name == "consultar_inventario" and message.status != "error"
        and any(item.get("tool_call_id") == message.tool_call_id
                for item in state.get("inventory_results", []))
        for message in lote
    )
    if (origen == "almacen" and destino is None and inventario_actual
            and not any(message.status == "error" or message.name in HANDOFF_TOOLS for message in lote)
            and state.get("required_parts") and not state.get("inventory_pending", True)):
        destino = evaluar_abastecimiento(state)["destination"]
        motivo = "Entregar inventario verificado"
    historial = list(state.get("handoff_history", []))
    contador = state.get("handoff_count", 0)
    errores = list(state.get("errors", []))
    iteraciones = dict(state.get("tool_iterations", {}))
    iteraciones[origen] = iteraciones.get(origen, 0) + 1

    if iteraciones[origen] >= MAX_TOOL_ITERATIONS:
        errores.append(f"Límite de herramientas alcanzado por {origen}")
        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [AIMessage(content=(
                "No fue posible completar la solicitud "
                "dentro del límite de operaciones permitido."
            ))],
        }

    if destino is None:
        return {"next_agent": origen, "tool_iterations": iteraciones}

    def rechazo(error):
        return {"next_agent": "finalizar", "tool_iterations": iteraciones,
                "errors": errores + [str(error)],
                "messages": [AIMessage(content="No se pudo completar la transferencia.")]}

    try:
        validate_handoff(origen, destino, motivo, AGENT_NODES, state.get("request_revision"))
    except ValueError as error:
        return rechazo(error)

    selected = selected_handoff(state["messages"])
    datos = None
    if selected is not None:
        try:
            datos = json.loads(selected.content)
        except (ValueError, TypeError):
            pass
    consulta_inventario = None
    if selected is not None and selected.name == "solicitar_inventario":
        if isinstance(datos, dict) and isinstance(datos.get("consulta"), str):
            consulta_inventario = datos["consulta"]

    if destino == origen:
        errores.append("Transferencia al mismo agente")
        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [AIMessage(content="No se pudo completar la transferencia.")],
        }

    if contador >= MAX_HANDOFFS:
        errores.append("Límite de transferencias alcanzado")
        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [AIMessage(content=(
                "No fue posible completar la solicitud "
                "tras varios intentos de transferencia."
            ))],
        }

    repuesto_pendiente = None
    abastecimiento = evaluar_abastecimiento(state)
    if origen == "almacen" and destino in {"compras", "ventas"} and abastecimiento["destination"] != destino:
        return rechazo(ValueError("Destino incompatible con la disponibilidad de inventario verificada"))
    if origen == "compras" and destino == "ventas" and abastecimiento["destination"] != "compras":
        return rechazo(ValueError("Faltante de inventario sin vigencia confirmada"))
    if origen == "software" and destino == "ventas":
        alcance = datos.get("alcance") if isinstance(datos, dict) else None
        if alcance != "solo_servicio" or not software_comercial_elegible(state):
            return rechazo(ValueError("Software solo puede transferir a Ventas un servicio sin repuestos"))
    if origen == "tecnico" and destino == "ventas":
        alcance = datos.get("alcance") if isinstance(datos, dict) else None
        if alcance == "repuestos":
            nombre = datos.get("nombre_repuesto")
            cantidad = datos.get("cantidad")
            if repuesto_confirmado(state, nombre) and type(cantidad) is int and cantidad > 0:
                repuesto_pendiente = {"name": nombre.strip(), "quantity": cantidad}
                destino = "almacen"
            else:
                return {"next_agent": "finalizar", "tool_iterations": iteraciones,
                        "messages": [AIMessage(content=(
                            "Para verificar disponibilidad y cotizar el reemplazo, "
                            "¿qué tipo o modelo exacto de repuesto indicó el técnico? "
                            "Si no lo sabes, necesitamos una revisión para identificarlo."
                        ))]}
        elif alcance != "solo_servicio":
            return {"next_agent": "finalizar", "tool_iterations": iteraciones,
                    "messages": [AIMessage(content=(
                        "Antes de cotizar, necesito aclarar si solicitas únicamente "
                        "una revisión de diagnóstico o una reparación con repuestos pendientes de verificar."
                    ))]}

    if origen == "tecnico" and destino == "almacen" and repuesto_pendiente is None:
        repuesto_pendiente = extraer_repuesto_handoff(state["messages"])
        if repuesto_pendiente is None:
            errores.append("Transferencia a Almacén sin repuesto válido")
            return {
                "next_agent": "finalizar",
                "tool_iterations": iteraciones,
                "errors": errores,
                "messages": [AIMessage(content=(
                    "No fue posible identificar un repuesto válido para consultar."
                ))],
            }

    if repuesto_pendiente is not None and not repuesto_confirmado(state, repuesto_pendiente["name"]):
        return {"next_agent": "finalizar", "tool_iterations": iteraciones,
                "messages": [AIMessage(content=(
                    "¿Qué tipo o modelo exacto de repuesto indicó el técnico? "
                    "No puedo elegir una variante ni confirmar compatibilidad solo con un nombre genérico."
                ))]}

    # Impedir cotizaciones mientras falte verificar inventario.
    if (
        origen == "almacen"
        and destino == "ventas"
        and (state.get("inventory_pending", False)
             or (state.get("required_parts") and not all(
                 any(item.get("requested_name") == part["name"] and item.get("quantity") == part["quantity"]
                     for item in inventario_vigente(state)) for part in state["required_parts"])))
    ):
        errores.append("Inventario pendiente de verificar")
        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [AIMessage(content=(
                "No es posible continuar con la cotización "
                "porque falta verificar el inventario."
            ))],
        }

    try:
        record = make_handoff_record(state, origen, destino, motivo, AGENT_NODES)
    except ValueError as error:
        return rechazo(error)
    historial.append({"origen": origen, "destino": destino})
    actualizacion = {
        "next_agent": destino,
        "handoff_count": contador + 1,
        "handoff_history": historial,
        "tool_iterations": iteraciones,
        "handoff_records": [*state.get("handoff_records", []), record],
    }
    if consulta_inventario is not None:
        actualizacion["inventory_query"] = consulta_inventario
    if destino == "almacen":
        required = list(state.get("required_parts", []))
        if repuesto_pendiente:
            # Conservar otros componentes; una cantidad nueva sustituye la
            # solicitud anterior de esa referencia, sin acumular ambas.
            required = [part for part in required if part.get("name") != repuesto_pendiente["name"]]
            required.append(repuesto_pendiente)
        actualizacion.update(preparar_inventario(state, required))
        if consulta_inventario is not None:
            actualizacion["inventory_pending"] = True
    if origen == "almacen" and destino == "ventas":
        actualizacion["inventory_requested_by"] = None
    if origen in {"almacen", "compras"} and destino in {"compras", "ventas"}:
        actualizacion.update(inventory_checks=abastecimiento["inventory_checks"],
                             out_of_stock_items=abastecimiento["out_of_stock_items"])
    if destino == "compras":
        actualizacion["supplier_offers"] = []
    if origen == "compras" and destino == "ventas":
        actualizacion.update(inventory_requested_by=None, quote_scope="repuestos")
    if repuesto_pendiente is not None:
        actualizacion["quote_scope"] = "repuestos"
    elif origen in {"tecnico", "software"} and destino == "ventas":
        actualizacion["quote_scope"] = "solo_servicio"
    elif origen == "almacen" and destino == "ventas":
        actualizacion["quote_scope"] = "repuestos"
    return actualizacion


def guardar_inventario(state: AgentState):
    """Registra inventario y verifica los repuestos requeridos."""
    resultados = inventario_vigente(state)
    errores = list(state.get("errors", []))
    requeridos = state.get("required_parts", [])

    for mensaje in reversed(state["messages"]):
        if not isinstance(mensaje, ToolMessage):
            break

        if mensaje.name != "consultar_inventario":
            continue

        if mensaje.status == "error":
            errores.append("Error al consultar inventario")
            continue

        try:
            resultado = json.loads(mensaje.content)

            if not isinstance(resultado, dict):
                raise ValueError("Resultado invalido")

            campos = {
                "requested_name", "name", "quantity",
                "stock", "unit_price", "available",
            }

            if not campos.issubset(resultado):
                raise ValueError("Faltan campos")

            nombre = resultado["requested_name"]
            cantidad = resultado["quantity"]
            stock = resultado["stock"]
            precio = resultado["unit_price"]
            disponible = resultado["available"]

            from decimal import Decimal, InvalidOperation

            if not isinstance(nombre, str) or not nombre.strip():
                raise ValueError("Nombre invalido")

            if type(cantidad) is not int or cantidad <= 0:
                raise ValueError("Cantidad invalida")

            if type(stock) is not int or stock < 0:
                raise ValueError("Stock invalido")

            if type(disponible) is not bool:
                raise ValueError("Disponibilidad invalida")

            try:
                precio_decimal = Decimal(str(precio))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("Precio invalido")

            if not precio_decimal.is_finite() or precio_decimal < 0:
                raise ValueError("Precio invalido")

            if disponible != (stock >= cantidad):
                raise ValueError("Disponibilidad inconsistente")

            if requeridos and not any(part.get("name") == nombre and part.get("quantity") == cantidad
                                      for part in requeridos):
                raise ValueError("Resultado ajeno al requerimiento")

            resultado["tool_call_id"] = mensaje.tool_call_id

            resultados = [
                item for item in resultados
                if item.get("tool_call_id") != mensaje.tool_call_id
                and (item.get("requested_name"), item.get("quantity")) != (nombre, cantidad)
            ]
            resultados.append(resultado)

        except (ValueError, TypeError):
            errores.append("Resultado de inventario inválido")

    def coincide(repuesto, resultado):
        return (
            isinstance(resultado, dict)
            and resultado.get("requested_name") == repuesto.get("name")
            and resultado.get("quantity") == repuesto.get("quantity")
        )

    completos = bool(requeridos) and all(
        any(coincide(repuesto, resultado) for resultado in resultados)
        for repuesto in requeridos
    )

    return {
        "inventory_results": resultados,
        "inventory_revision": state.get("request_revision", 0) if resultados else None,
        "inventory_pending": not completos if requeridos else
            state.get("inventory_pending", False),
        "errors": errores,
    }


def auditar_soporte(state: AgentState):
    return registrar_handoff(state, "soporte")


def auditar_tecnico(state: AgentState):
    return registrar_handoff(state, "tecnico")


def auditar_ventas(state: AgentState):
    return registrar_handoff(state, "ventas")


def auditar_almacen(state: AgentState):
    return registrar_handoff(state, "almacen")


def auditar_software(state: AgentState):
    return registrar_handoff(state, "software")


def auditar_compras(state: AgentState):
    return registrar_handoff(state, "compras")


def auditar_facturacion(state: AgentState):
    return registrar_handoff(state, "facturacion")


def auditar_logistica(state: AgentState):
    return registrar_handoff(state, "logistica")


def route_next_agent(state: AgentState):
    return state.get("next_agent") or "finalizar"


def route_entry(state: AgentState):
    """Retoma al agente activo; las conversaciones nuevas empiezan en Soporte."""
    agente = state.get("current_agent", "soporte")
    return agente if agente in AGENT_NODES else "soporte"


def preparar_turno(state: AgentState):
    """Reinicia controles tras recuperar el historial, sin borrar datos de negocio."""
    messages = state.get("messages", [])
    inicio = next(
        (i for i in range(len(messages) - 1, -1, -1)
         if isinstance(messages[i], HumanMessage)),
        state.get("turn_start_index", 0),
    )
    return {
        "turn_start_index": inicio,
        "ticket_preparation_ready": False,
        "handoff_count": 0,
        "handoff_history": [],
        "handoff_records": [],
        "tool_iterations": {},
        "errors": [],
        "next_agent": None,
    }


def build_graph(checkpointer=None, *, financial_repository=None, ticket_writes=False):
    """Construye la misma red; el consumidor puede aportar su checkpointer.

    Sin checkpointer admite invoke(state) y el historial gestionado por Conversation.
    La API aporta MemorySaver y thread_id para conservar conversaciones.
    """
    if financial_repository is not None and checkpointer is None:
        raise ValueError("Preparación financiera requiere checkpointer explícito")
    builder = StateGraph(AgentState, context_schema=FinancialContext)
    for name, node in AGENT_NODES.items():
        if name == "soporte" and financial_repository is not None:
            def support_entry(state: AgentState, runtime: Runtime[FinancialContext]):
                customer = (runtime.context or {}).get("authenticated_customer_id")
                return soporte_node(state, authenticated_customer_id=customer) if customer is not None else soporte_node(state)
            node = support_entry
        if name == "garantia" and financial_repository is not None:
            def warranty_entry(state: AgentState, runtime: Runtime[FinancialContext]):
                return garantia_node(state, repository=financial_repository,
                    authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"))
            node = warranty_entry
        if name == "logistica" and financial_repository is not None:
            def logistics_entry(state: AgentState, runtime: Runtime[FinancialContext]):
                return logistica_node(state, repository=financial_repository,
                    authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"))
            node = logistics_entry
        if name == "facturacion" and financial_repository is not None:
            # Trusted invocation context is not checkpointed or model-generated.
            def financial_entry(state: AgentState, runtime: Runtime[FinancialContext]):
                return facturacion_node(state, repository=financial_repository,
                    authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"))
            node = financial_entry
        builder.add_node(name, node)

    if ticket_writes and (financial_repository is None or checkpointer is None):
        raise ValueError("Creación de tickets requiere repositorio y checkpointer")

    def preparar_ticket(state: AgentState, runtime: Runtime[FinancialContext]):
        from app.agents.decentralized.ticket_operations import validate_pending_ticket_operation
        if state.get("ticket_correction_required"):
            raise ValueError("La operación requiere reconciliación")
        operation = validate_pending_ticket_operation(state.get("pending_ticket_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        return {"pending_ticket_operation": operation, "ticket_preparation_ready": False,
                "messages": [AIMessage(content="La solicitud está preparada y todavía no se creó un ticket. Responde continuar para registrar esta misma solicitud y derivarla al especialista.")]}

    def ejecutar_ticket(state: AgentState, config, runtime: Runtime[FinancialContext]):
        from app.agents.decentralized.ticket_operations import validate_pending_ticket_operation
        from app.database.decentralized_repository import _id
        operation = validate_pending_ticket_operation(state.get("pending_ticket_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        if state.get("ticket_correction_required") or state.get("ticket_id") is not None:
            raise ValueError("Operación de ticket incompatible")
        # Check the completed preparation checkpoint, not the current task's
        # private namespace. API invokes with durability='sync'. Fail closed.
        saved = checkpointer.get_tuple({"configurable": {
            "thread_id": config["configurable"]["thread_id"], "checkpoint_ns": ""}})
        if saved is None or saved.checkpoint.get("channel_values", {}).get("pending_ticket_operation") != operation:
            raise RuntimeError("Operación pendiente no confirmada en checkpoint")
        row = financial_repository.create_ticket(**operation["payload"])
        if any(row.get(key) != value for key, value in operation["payload"].items()):
            raise RuntimeError("Respuesta de ticket incompatible")
        ticket_id = _id(row.get("id"))
        from app.agents.decentralized.policy import triaje_soporte
        kind = operation["payload"]["request_type"]
        destination = {"SALE": "ventas", "PC_BUILD": "ventas", "SUPPORT": "software",
                       "WARRANTY_CLAIM": "garantia", "REPAIR": "tecnico"}[kind]
        if kind == "REPAIR" and triaje_soporte({"messages": [HumanMessage(content=operation["payload"]["failure_description"])]}) == "software":
            destination = "software"
        transfer = handoff("soporte", "transferir_a_" + destination,
                           motivo="Continuar solicitud con ticket persistido y cliente autenticado")
        transfer["messages"].insert(0, AIMessage(content="Tu solicitud quedó registrada con el código " + row["code"] + "."))
        return {**transfer, "ticket_id": ticket_id, "ticket_code": row["code"],
                "ticket_status": row["status"], "request_type": kind,
                "pending_ticket_operation": None, "ticket_preparation_ready": False}

    if ticket_writes:
        builder.add_node("preparar_ticket", preparar_ticket)
        builder.add_node("ejecutar_ticket", ejecutar_ticket)
        builder.add_edge("preparar_ticket", "ejecutar_ticket")
        builder.add_edge("ejecutar_ticket", "soporte_tools")

    def preparar_garantia(state: AgentState, runtime: Runtime[FinancialContext]):
        operation = validate_pending_warranty_operation(state.get("pending_warranty_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        return {"pending_warranty_operation": operation}

    def ejecutar_garantia(state: AgentState, runtime: Runtime[FinancialContext]):
        operation = validate_pending_warranty_operation(state.get("pending_warranty_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        if state.get("ticket_id") != operation["payload"]["ticket_id"]:
            raise ValueError("Ticket pendiente incompatible")
        row = financial_repository.create_warranty_claim(**operation["payload"])
        ticket = financial_repository.get_ticket(customer_id=operation["payload"]["customer_id"], ticket_id=row["ticket_id"])
        patch = {"pending_warranty_operation": None, "warranty_preparation_ready": False,
                 "warranty_claim_id": row["id"], "claim_code": row["claim_code"],
                 "warranty_id": row["warranty_id"], "ticket_status": ticket["status"],
                 "warranty_claim": {"reason": row["reason"], "status": row["status"]}}
        try:
            financial_repository.get_logistics_context(customer_id=operation["payload"]["customer_id"], ticket_id=row["ticket_id"])
        except (ValueError, LookupError):
            return {**patch, "messages": [AIMessage(content="Reclamo persistido; sus condiciones actuales no permiten coordinar ingreso. No hay reparación aprobada.")]}
        return {**patch, **handoff("garantia", "transferir_a_logistica", motivo="Coordinar ingreso de reclamo persistido IN_REVIEW")}

    builder.add_node("preparar_garantia", preparar_garantia)
    builder.add_node("ejecutar_garantia", ejecutar_garantia)
    builder.add_edge("preparar_garantia", "ejecutar_garantia")
    builder.add_conditional_edges("ejecutar_garantia", tools_condition, {"tools": "garantia_tools", "__end__": END})

    def warranty_route(state):
        if tools_condition(state) == "tools":
            return "tools"
        return "prepare" if (financial_repository is not None and state.get("pending_warranty_operation")
                             and state.get("warranty_preparation_ready") is True) else "__end__"

    def preparar_pago(state: AgentState, runtime: Runtime[FinancialContext]):
        pending = validate_pending_payment_operation(state.get("pending_payment_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        # A separate superstep records exactly the prepared operation. No LLM.
        return {"pending_payment_operation": pending}

    def ejecutar_pago(state: AgentState, runtime: Runtime[FinancialContext]):
        validate_pending_payment_operation(state.get("pending_payment_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        return {"messages": [AIMessage(content="La operación pendiente fue recuperada. La escritura financiera continúa deshabilitada; no se ha registrado ni confirmado un pago.")]}

    builder.add_node("preparar_pago", preparar_pago)
    builder.add_node("ejecutar_pago", ejecutar_pago)
    builder.add_edge("preparar_pago", "ejecutar_pago")
    builder.add_edge("ejecutar_pago", END)

    def preparar_logistica(state: AgentState, runtime: Runtime[FinancialContext]):
        operation = validate_pending_logistics_operation(state.get("pending_logistics_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        return {"pending_logistics_operation": operation}

    def ejecutar_logistica(state: AgentState, runtime: Runtime[FinancialContext]):
        operation = validate_pending_logistics_operation(state.get("pending_logistics_operation"),
            authenticated_customer_id=(runtime.context or {}).get("authenticated_customer_id"),
            request_revision=state.get("request_revision"))
        if state.get("ticket_id") != operation["payload"]["ticket_id"]:
            raise ValueError("Ticket pendiente incompatible")
        row = financial_repository.create_initial_logistics(**operation["payload"])
        return {"pending_logistics_operation": None, "logistics_record_id": row["id"],
                "logistics_preparation_ready": False,
                "logistics": {key:row.get(key) for key in ("mode", "status", "courier_company", "shipping_address",
                               "recipient_name", "recipient_phone", "tracking_number", "scheduled_date", "received_at", "delivered_at")},
                "messages": [AIMessage(content="El registro logístico está confirmado en el sistema. Su estado es " + row["status"] + ". Este registro no confirma recepción física, preparación, despacho ni entrega.")]}

    builder.add_node("preparar_logistica", preparar_logistica)
    builder.add_node("ejecutar_logistica", ejecutar_logistica)
    builder.add_edge("preparar_logistica", "ejecutar_logistica")
    builder.add_edge("ejecutar_logistica", END)

    def logistics_route(state):
        if tools_condition(state) == "tools":
            return "tools"
        return "prepare" if (financial_repository is not None and state.get("pending_logistics_operation")
                             and state.get("logistics_preparation_ready") is True) else "__end__"

    def financial_route(state):
        if tools_condition(state) == "tools":
            return "tools"
        return "prepare" if financial_repository is not None and state.get("pending_payment_operation") else "__end__"

    for name, tools in (
        ("soporte", soporte_tools),
        ("tecnico", tecnico_tools),
        ("ventas", ventas_tools),
        ("almacen", almacen_tools),
        ("software", software_tools),
        ("compras", compras_tools),
        ("facturacion", facturacion_tools),
        ("logistica", logistica_tools),
        ("garantia", garantia_tools),
    ):
        if name == "soporte" and financial_repository is not None:
            from app.agents.decentralized.tools.soporte_tools import authenticated_ticket_tool
            tools = [authenticated_ticket_tool(financial_repository)
                     if item.name == "consultar_estado_ticket" else item for item in tools]
        builder.add_node(f"{name}_tools", ToolNode(tools, handle_tool_errors=True))

    builder.add_node("guardar_inventario", guardar_inventario)
    builder.add_node("auditar_soporte", auditar_soporte)
    builder.add_node("auditar_tecnico", auditar_tecnico)
    builder.add_node("auditar_ventas", auditar_ventas)
    builder.add_node("auditar_almacen", auditar_almacen)
    builder.add_node("auditar_software", auditar_software)
    builder.add_node("auditar_compras", auditar_compras)
    builder.add_node("auditar_facturacion", auditar_facturacion)
    builder.add_node("auditar_logistica", auditar_logistica)
    builder.add_node("auditar_garantia", lambda state: registrar_handoff(state, "garantia"))

    builder.add_node("preparar_turno", preparar_turno)
    builder.add_edge(START, "preparar_turno")
    builder.add_conditional_edges("preparar_turno", route_entry,
                                  {name: name for name in AGENT_NODES})
    for agente in AGENT_NODES:
        if agente == "soporte" and ticket_writes:
            def support_route(state):
                if tools_condition(state) == "tools":
                    return "tools"
                return "prepare" if state.get("ticket_preparation_ready") and not state.get("ticket_correction_required") else "__end__"
            builder.add_conditional_edges(agente, support_route,
                {"tools": "soporte_tools", "prepare": "preparar_ticket", "__end__": END})
            continue
        if agente == "garantia":
            builder.add_conditional_edges(agente, warranty_route,
                {"tools": "garantia_tools", "prepare": "preparar_garantia", "__end__": END})
            continue
        if agente == "logistica":
            builder.add_conditional_edges(agente, logistics_route,
                {"tools": "logistica_tools", "prepare": "preparar_logistica", "__end__": END})
            continue
        if agente == "facturacion":
            builder.add_conditional_edges(agente, financial_route,
                {"tools": "facturacion_tools", "prepare": "preparar_pago", "__end__": END})
            continue
        builder.add_conditional_edges(
            agente,
            tools_condition,
            {"tools": f"{agente}_tools", "__end__": END},
        )

    builder.add_edge("soporte_tools", "auditar_soporte")
    builder.add_edge("tecnico_tools", "auditar_tecnico")
    builder.add_edge("ventas_tools", "auditar_ventas")
    builder.add_edge("almacen_tools", "guardar_inventario")
    builder.add_edge("guardar_inventario", "auditar_almacen")
    builder.add_edge("software_tools", "auditar_software")
    builder.add_edge("compras_tools", "auditar_compras")
    builder.add_edge("facturacion_tools", "auditar_facturacion")
    builder.add_edge("logistica_tools", "auditar_logistica")
    builder.add_edge("garantia_tools", "auditar_garantia")

    rutas = {**{name: name for name in AGENT_NODES}, "finalizar": END}
    for auditor in (
        "auditar_soporte", "auditar_tecnico",
        "auditar_almacen", "auditar_ventas",
        "auditar_software",
        "auditar_compras",
        "auditar_facturacion",
        "auditar_logistica",
        "auditar_garantia",
    ):
        builder.add_conditional_edges(auditor, route_next_agent, rutas)

    # Static interrupt forces a saved checkpoint before the execution superstep.
    # Resume requires a trusted caller using invoke(None, context=...) explicitly.
    interrupts = ["ejecutar_pago", "ejecutar_logistica", "ejecutar_garantia"] if financial_repository is not None else []
    if ticket_writes:
        interrupts.append("ejecutar_ticket")
    return builder.compile(checkpointer=checkpointer, interrupt_before=interrupts or None)


# Compatible con scripts y Conversation que invocan sin thread_id.
graph = build_graph()

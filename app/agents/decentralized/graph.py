import json

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.soporte import soporte_node, soporte_tools
from app.agents.decentralized.tecnico import tecnico_node, tecnico_tools
from app.agents.decentralized.ventas import ventas_node, ventas_tools
from app.agents.decentralized.almacen import almacen_node, almacen_tools

MAX_HANDOFFS = 5
MAX_TOOL_ITERATIONS = 6

HANDOFF_TOOLS = {
    "transferir_a_tecnico": "tecnico",
    "transferir_a_ventas": "ventas",
    "transferir_a_almacen": "almacen",
}


def detectar_handoff(messages):
    """Identifica la última transferencia ejecutada correctamente."""
    tool_messages = []
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            tool_messages.append(message)
        else:
            break

    for message in reversed(tool_messages):
        if message.status == "error":
            continue
        destino = HANDOFF_TOOLS.get(message.name)
        if destino:
            return destino
    return None


def extraer_repuesto_handoff(messages):
    """Valida los datos estructurados de transferir_a_almacen."""
    for mensaje in reversed(messages):
        if not isinstance(mensaje, ToolMessage):
            break
        if mensaje.name != "transferir_a_almacen":
            continue
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
    if origen == "tecnico" and destino == "almacen":
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

    # Impedir cotizaciones mientras falte verificar inventario.
    if (
        origen == "almacen"
        and destino == "ventas"
        and state.get("inventory_pending", False)
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

    historial.append({"origen": origen, "destino": destino})
    actualizacion = {
        "next_agent": destino,
        "handoff_count": contador + 1,
        "handoff_history": historial,
        "tool_iterations": iteraciones,
    }
    if repuesto_pendiente is not None:
        repuestos = list(state.get("required_parts", []))
        if repuesto_pendiente not in repuestos:
            repuestos.append(repuesto_pendiente)
        actualizacion["required_parts"] = repuestos
        actualizacion["inventory_pending"] = True
    return actualizacion


def guardar_inventario(state: AgentState):
    """Registra inventario y verifica los repuestos requeridos."""
    resultados = list(state.get("inventory_results", []))
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

            resultado["tool_call_id"] = mensaje.tool_call_id

            resultados = [
                item for item in resultados
                if item.get("tool_call_id") != mensaje.tool_call_id
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


def route_next_agent(state: AgentState):
    return state.get("next_agent") or "finalizar"


builder = StateGraph(AgentState)
for name, node in (
    ("soporte", soporte_node),
    ("tecnico", tecnico_node),
    ("ventas", ventas_node),
    ("almacen", almacen_node),
):
    builder.add_node(name, node)

for name, tools in (
    ("soporte", soporte_tools),
    ("tecnico", tecnico_tools),
    ("ventas", ventas_tools),
    ("almacen", almacen_tools),
):
    builder.add_node(f"{name}_tools", ToolNode(tools, handle_tool_errors=True))

builder.add_node("guardar_inventario", guardar_inventario)
builder.add_node("auditar_soporte", auditar_soporte)
builder.add_node("auditar_tecnico", auditar_tecnico)
builder.add_node("auditar_ventas", auditar_ventas)
builder.add_node("auditar_almacen", auditar_almacen)

builder.add_edge(START, "soporte")
for agente in ("soporte", "tecnico", "almacen", "ventas"):
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

rutas = {
    "soporte": "soporte",
    "tecnico": "tecnico",
    "almacen": "almacen",
    "ventas": "ventas",
    "finalizar": END,
}
for auditor in (
    "auditar_soporte", "auditar_tecnico",
    "auditar_almacen", "auditar_ventas",
):
    builder.add_conditional_edges(auditor, route_next_agent, rutas)

graph = builder.compile()
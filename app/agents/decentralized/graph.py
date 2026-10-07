
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.soporte import soporte_node, soporte_tools
from app.agents.decentralized.tecnico import tecnico_node, tecnico_tools
from app.agents.decentralized.ventas import ventas_node, ventas_tools


# =========================================================
# CONFIGURACIÓN
# =========================================================

MAX_HANDOFFS = 5
MAX_TOOL_ITERATIONS = 6

# Herramientas que transfieren el control
HANDOFF_TOOLS = {
    "transferir_a_tecnico": "tecnico",
    "transferir_a_ventas": "ventas",
}


# =========================================================
# DETECCIÓN DE TRANSFERENCIAS
# =========================================================

def detectar_handoff(messages):
    """
    Identifica si se ejecutó una herramienta de transferencia.

    No depende del texto devuelto por la herramienta.
    """

    tool_messages = []

    # Recuperamos los resultados de la última ejecución
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            tool_messages.append(message)
        else:
            break

    if not tool_messages:
        return None

    # Verificamos las herramientas ejecutadas
    for message in reversed(tool_messages):
        if message.status == "error":
            continue

        destino = HANDOFF_TOOLS.get(message.name)

        if destino:
            return destino

    return None


# =========================================================
# ACTUALIZACIÓN DEL ESTADO
# =========================================================

def registrar_handoff(state: AgentState, origen: str):
    """
    Registra las transferencias entre agentes y controla
    el número de ejecuciones de herramientas.
    """

    destino = detectar_handoff(state["messages"])

    historial = list(state.get("handoff_history", []))
    contador = state.get("handoff_count", 0)
    errores = list(state.get("errors", []))

    # -----------------------------------------------------
    # CONTROL DE ITERACIONES DE HERRAMIENTAS
    # -----------------------------------------------------

    iteraciones = dict(state.get("tool_iterations", {}))

    iteraciones[origen] = (
        iteraciones.get(origen, 0) + 1
    )

    # Detener ejecuciones excesivas
    if iteraciones[origen] >= MAX_TOOL_ITERATIONS:
        errores.append(
            f"Límite de herramientas alcanzado por {origen}"
        )

        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible completar la solicitud "
                        "dentro del límite de operaciones permitido."
                    )
                )
            ],
        }

    # -----------------------------------------------------
    # SIN TRANSFERENCIA
    # -----------------------------------------------------

    if destino is None:
        return {
            "next_agent": origen,
            "tool_iterations": iteraciones,
        }

    # -----------------------------------------------------
    # TRANSFERENCIA AL MISMO AGENTE
    # -----------------------------------------------------

    if destino == origen:
        errores.append("Transferencia al mismo agente")

        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [
                AIMessage(
                    content="No se pudo completar la transferencia."
                )
            ],
        }

    # -----------------------------------------------------
    # LÍMITE DE TRANSFERENCIAS
    # -----------------------------------------------------

    if contador >= MAX_HANDOFFS:
        errores.append("Límite de transferencias alcanzado")

        return {
            "next_agent": "finalizar",
            "tool_iterations": iteraciones,
            "errors": errores,
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible completar la solicitud "
                        "tras varios intentos de transferencia."
                    )
                )
            ],
        }

    # -----------------------------------------------------
    # REGISTRO DE TRANSFERENCIA
    # -----------------------------------------------------

    historial.append({
        "origen": origen,
        "destino": destino,
    })

    return {
        "next_agent": destino,
        "handoff_count": contador + 1,
        "handoff_history": historial,
        "tool_iterations": iteraciones,
    }


# =========================================================
# NODOS DE CONTROL
# =========================================================

def auditar_soporte(state: AgentState):
    return registrar_handoff(state, "soporte")


def auditar_tecnico(state: AgentState):
    return registrar_handoff(state, "tecnico")


def auditar_ventas(state: AgentState):
    return registrar_handoff(state, "ventas")


def route_next_agent(state: AgentState):
    """
    Devuelve el siguiente agente indicado
    por el estado compartido.
    """
    return state.get("next_agent") or "finalizar"


# =========================================================
# CONSTRUCCIÓN DEL GRAFO
# =========================================================

builder = StateGraph(AgentState)

# Agentes
builder.add_node("soporte", soporte_node)
builder.add_node("tecnico", tecnico_node)
builder.add_node("ventas", ventas_node)

# Herramientas con manejo de errores
builder.add_node(
    "soporte_tools",
    ToolNode(soporte_tools, handle_tool_errors=True)
)

builder.add_node(
    "tecnico_tools",
    ToolNode(tecnico_tools, handle_tool_errors=True)
)

builder.add_node(
    "ventas_tools",
    ToolNode(ventas_tools, handle_tool_errors=True)
)

# Auditoría de transferencias
builder.add_node("auditar_soporte", auditar_soporte)
builder.add_node("auditar_tecnico", auditar_tecnico)
builder.add_node("auditar_ventas", auditar_ventas)


# =========================================================
# PUNTO DE ENTRADA
# =========================================================

builder.add_edge(START, "soporte")


# =========================================================
# EJECUCIÓN DE LOS AGENTES
# =========================================================

for agente in ("soporte", "tecnico", "ventas"):
    builder.add_conditional_edges(
        agente,
        tools_condition,
        {
            "tools": f"{agente}_tools",
            "__end__": END,
        },
    )


# =========================================================
# EJECUCIÓN Y AUDITORÍA DE HERRAMIENTAS
# =========================================================

builder.add_edge("soporte_tools", "auditar_soporte")
builder.add_edge("tecnico_tools", "auditar_tecnico")
builder.add_edge("ventas_tools", "auditar_ventas")


# =========================================================
# ENRUTAMIENTO DESCENTRALIZADO
# =========================================================

# Cada agente puede continuar o transferir el control.
# No existe un supervisor central.

rutas = {
    "soporte": "soporte",
    "tecnico": "tecnico",
    "ventas": "ventas",
    "finalizar": END,
}

for auditor in (
    "auditar_soporte",
    "auditar_tecnico",
    "auditar_ventas",
):
    builder.add_conditional_edges(
        auditor,
        route_next_agent,
        rutas,
    )


# =========================================================
# COMPILACIÓN
# =========================================================

graph = builder.compile()

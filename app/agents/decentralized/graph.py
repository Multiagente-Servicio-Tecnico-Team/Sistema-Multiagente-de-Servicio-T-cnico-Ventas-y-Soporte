from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.soporte import soporte_node, soporte_tools
from app.agents.decentralized.tecnico import tecnico_node, tecnico_tools
from app.agents.decentralized.ventas import ventas_node, ventas_tools

# =========================================================
# ROUTERS
# =========================================================

def route_soporte_tools(state: AgentState):
    """
    Decide qué agente debe continuar después de ejecutar
    una herramienta del agente de Soporte.
    """

    ultimo_mensaje = state["messages"][-1]

    # Handoff hacia el agente Técnico
    if "TRANSFERIR_TECNICO" in ultimo_mensaje.content:
        return "tecnico"

    # Handoff hacia el agente de Ventas
    if "TRANSFERIR_VENTAS" in ultimo_mensaje.content:
        return "ventas"

    # Si fue una herramienta normal de Soporte,
    # regresamos al agente de Soporte
    return "soporte"

def route_tecnico_tools(state: AgentState):
    """
    Decide qué agente debe continuar después de ejecutar
    una herramienta del agente Técnico.
    """
    ultimo_mensaje = state["messages"][-1]

    # Si Técnico ejecutó explícitamente el handoff a Ventas
    if "TRANSFERIR_VENTAS" in ultimo_mensaje.content:
        return "ventas"

    # Si Técnico acaba de realizar un diagnóstico,
    # verificamos si la solicitud original también pedía
    # precio o cotización.
    if getattr(ultimo_mensaje, "name", None) == "diagnosticar_problema":
        mensaje_usuario = state["messages"][0].content.lower()

        palabras_comerciales = [
            "precio",
            "cuesta",
            "costo",
            "cotizacion",
            "cotización",
            "presupuesto",
        ]

        if any(
            palabra in mensaje_usuario
            for palabra in palabras_comerciales
        ):
            return "ventas"

    # Si solo era un diagnóstico, vuelve al agente Técnico
    return "tecnico"

def route_ventas_tools(state: AgentState):
    """
    Decide qué agente debe continuar después de ejecutar
    una herramienta del agente de Ventas.
    """
    ultimo_mensaje = state["messages"][-1]

    if "TRANSFERIR_TECNICO" in ultimo_mensaje.content:
        return "tecnico"

    return "ventas"

# 1. Creamos el grafo utilizando nuestro estado compartido
builder = StateGraph(AgentState)


# =========================================================
# AGENTE DE SOPORTE
# =========================================================

# Agregamos el agente de Soporte como nodo
builder.add_node("soporte", soporte_node)

# Nodo encargado de ejecutar las tools de Soporte
soporte_tool_node = ToolNode(soporte_tools)
builder.add_node("soporte_tools", soporte_tool_node)


# =========================================================
# AGENTE TÉCNICO
# =========================================================

# Agregamos el agente Técnico como nodo
builder.add_node("tecnico", tecnico_node)

# Nodo encargado de ejecutar las tools del agente Técnico
tecnico_tool_node = ToolNode(tecnico_tools)
builder.add_node("tecnico_tools", tecnico_tool_node)

# =========================================================
# AGENTE DE VENTAS
# =========================================================

# Agregamos el agente de Ventas como nodo
builder.add_node("ventas", ventas_node)

# Nodo encargado de ejecutar las tools del agente de Ventas
ventas_tool_node = ToolNode(ventas_tools)
builder.add_node("ventas_tools", ventas_tool_node)


# =========================================================
# INICIO DEL GRAFO
# =========================================================

# Por ahora el grafo comienza en Soporte
builder.add_edge(START, "soporte")


# =========================================================
# FLUJO DE SOPORTE
# =========================================================

# Después de ejecutar Soporte:
# - si pidió una tool -> va a soporte_tools
# - si no pidió una tool -> termina
builder.add_conditional_edges(
    "soporte",
    tools_condition,
    {
        "tools": "soporte_tools",
        "__end__": END,
    },
)


# Después de ejecutar una tool de Soporte:
# - si solicitó transferencia -> va a Técnico
# - si fue una tool normal -> regresa a Soporte
builder.add_conditional_edges(
    "soporte_tools",
    route_soporte_tools,
    {
        "tecnico": "tecnico",
        "soporte": "soporte",
        "ventas": "ventas",
    },
)


# =========================================================
# FLUJO DEL AGENTE TÉCNICO
# =========================================================

# Después de ejecutar Técnico:
# - si pidió una tool -> va a tecnico_tools
# - si no pidió una tool -> termina
builder.add_conditional_edges(
    "tecnico",
    tools_condition,
    {
        "tools": "tecnico_tools",
        "__end__": END,
    },
)

# Después de ejecutar una tool de Técnico:
# - si solicitó transferencia -> va a Ventas
# - si fue diagnóstico -> regresa a Técnico
builder.add_conditional_edges(
    "tecnico_tools",
    route_tecnico_tools,
    {
        "ventas": "ventas",
        "tecnico": "tecnico",
    },
)

# =========================================================
# FLUJO DEL AGENTE DE VENTAS
# =========================================================

# Después de ejecutar Ventas:
# - si pidió una tool -> va a ventas_tools
# - si no pidió una tool -> termina
builder.add_conditional_edges(
    "ventas",
    tools_condition,
    {
        "tools": "ventas_tools",
        "__end__": END,
    },
)

# Después de ejecutar una tool de Ventas:
# - si solicitó transferencia -> va a Técnico
# - si fue una cotización -> regresa a Ventas
builder.add_conditional_edges(
    "ventas_tools",
    route_ventas_tools,
    {
        "tecnico": "tecnico",
        "ventas": "ventas",
    },
)

# =========================================================
# COMPILACIÓN DEL GRAFO
# =========================================================

graph = builder.compile()
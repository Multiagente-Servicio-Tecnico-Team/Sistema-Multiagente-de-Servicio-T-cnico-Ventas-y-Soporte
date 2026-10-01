from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.soporte import soporte_node, soporte_tools

# 1. Creamos el grafo utilizando nuestro estado compartido
builder = StateGraph(AgentState)

# 2. Agregamos el agente de Soporte como nodo
builder.add_node("soporte", soporte_node)

# 3. Creamos un nodo encargado de ejecutar las tools de Soporte
soporte_tool_node = ToolNode(soporte_tools)
builder.add_node("soporte_tools", soporte_tool_node)

# 4. El grafo comienza en Soporte
builder.add_edge(START, "soporte")

# 5. Después de ejecutar Soporte:
#    - si pidió una tool -> va a soporte_tools
#    - si no pidió una tool -> termina
builder.add_conditional_edges(
    "soporte",
    tools_condition,
    {
        "tools": "soporte_tools",
        "__end__": END,
    },
)

# 6. Después de ejecutar una tool, regresamos al agente de Soporte
builder.add_edge("soporte_tools", "soporte")

# 7. Compilamos el grafo
graph = builder.compile()
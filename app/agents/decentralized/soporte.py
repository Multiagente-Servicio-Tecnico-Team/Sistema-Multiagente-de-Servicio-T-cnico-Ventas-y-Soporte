from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.soporte_tools import consultar_estado_ticket


# Carga las variables del archivo .env
load_dotenv()

# Modelo LLM utilizado por el agente
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)

# Herramientas disponibles para el agente de Soporte
soporte_tools = [
    consultar_estado_ticket
]

# Vinculamos las herramientas con el LLM
soporte_llm = llm.bind_tools(soporte_tools)

# Instrucciones y responsabilidades del agente
SYSTEM_PROMPT = """
Eres el agente de Soporte de un sistema multiagente de servicio técnico,
ventas y soporte.

Tus responsabilidades son:
- Atender consultas generales de soporte.
- Ayudar al usuario con sus tickets.
- Utilizar consultar_estado_ticket cuando el usuario pregunte por
  el estado de un ticket.
- No inventar información sobre tickets.

Si una solicitud requiere conocimientos técnicos especializados,
debes indicar que debe ser transferida al agente Técnico.

Si la solicitud está relacionada con compras o productos,
debes indicar que debe ser transferida al agente de Ventas.
"""


def soporte_node(state: AgentState):
    """
    Nodo del agente de Soporte dentro del grafo descentralizado.
    """

    # Combinamos el System Prompt con el historial de mensajes
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    # El LLM procesa los mensajes y puede decidir utilizar una tool
    response = soporte_llm.invoke(messages)

    # Actualizamos el estado compartido
    return {
        "messages": [response],
        "current_agent": "soporte"
    }
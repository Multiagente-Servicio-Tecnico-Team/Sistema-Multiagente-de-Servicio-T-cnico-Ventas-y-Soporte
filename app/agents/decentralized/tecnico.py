from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.tecnico_tools import diagnosticar_problema


# Carga las variables del archivo .env
load_dotenv()


# Modelo LLM utilizado por el agente
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)


# Herramientas disponibles para el agente Técnico
tecnico_tools = [
    diagnosticar_problema
]


# Vinculamos las herramientas con el LLM
tecnico_llm = llm.bind_tools(tecnico_tools)


# Instrucciones y responsabilidades del agente
SYSTEM_PROMPT = """
Eres el agente Técnico de un sistema multiagente de servicio técnico,
ventas y soporte.

Tus responsabilidades son:
- Analizar los síntomas técnicos reportados por el usuario.
- Realizar un diagnóstico preliminar.
- Utilizar diagnosticar_problema cuando sea necesario analizar un síntoma.
- No inventar diagnósticos que no estén respaldados por la herramienta.

Si la solicitud corresponde al estado de un ticket o a una consulta
general de soporte, debes indicar que debe ser transferida al agente
de Soporte.

Si la solicitud está relacionada con compras, precios o productos,
debes indicar que debe ser transferida al agente de Ventas.
"""


def tecnico_node(state: AgentState):
    """
    Nodo del agente Técnico dentro del grafo descentralizado.
    """

    # Combinamos el System Prompt con el historial de mensajes
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    # El LLM procesa los mensajes y puede decidir utilizar una tool
    response = tecnico_llm.invoke(messages)

    # Actualizamos el estado compartido
    return {
        "messages": [response],
        "current_agent": "tecnico"
    }
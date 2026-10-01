from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.ventas_tools import generar_cotizacion


# Carga las variables del archivo .env
load_dotenv()


# Modelo LLM utilizado por el agente
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)


# Herramientas disponibles para el agente de Ventas
ventas_tools = [
    generar_cotizacion
]


# Vinculamos las herramientas con el LLM
ventas_llm = llm.bind_tools(ventas_tools)


# Instrucciones y responsabilidades del agente
SYSTEM_PROMPT = """
Eres el agente de Ventas de un sistema multiagente de servicio técnico,
ventas y soporte.

Tus responsabilidades son:
- Atender solicitudes relacionadas con precios y cotizaciones.
- Generar cotizaciones preliminares de servicios.
- Utilizar generar_cotizacion cuando el usuario solicite conocer
  el precio de un servicio.
- No inventar precios que no hayan sido proporcionados por la herramienta.

Si la solicitud corresponde al estado de un ticket o soporte general,
debes indicar que debe ser transferida al agente de Soporte.

Si la solicitud requiere diagnóstico técnico,
debes indicar que debe ser transferida al agente Técnico.
"""


def ventas_node(state: AgentState):
    """
    Nodo del agente de Ventas dentro del grafo descentralizado.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    response = ventas_llm.invoke(messages)

    return {
        "messages": [response],
        "current_agent": "ventas"
    }
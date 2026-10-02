from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.ventas_tools import (
    generar_cotizacion,
    transferir_a_tecnico,
)


# Carga las variables del archivo .env
load_dotenv()


# Modelo LLM utilizado por el agente
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    reasoning_effort="low",
    model_kwargs={
        "parallel_tool_calls": False,
    }
)


# Herramientas disponibles para el agente de Ventas
ventas_tools = [
    generar_cotizacion,
    transferir_a_tecnico,
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

Puedes recibir solicitudes que previamente fueron atendidas por otros
agentes del sistema.

IMPORTANTE:
- Si en el historial existe un ToolMessage con el resultado de
  diagnosticar_problema, considera que el diagnóstico técnico ya fue realizado.
- Si el diagnóstico ya fue realizado y el usuario solicita un precio
  o cotización, debes utilizar generar_cotizacion.
- En ese caso, no debes solicitar otro diagnóstico ni transferir
  nuevamente al agente Técnico.
- Para una solicitud de reparación, utiliza generar_cotizacion
  indicando "reparacion" como servicio.
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
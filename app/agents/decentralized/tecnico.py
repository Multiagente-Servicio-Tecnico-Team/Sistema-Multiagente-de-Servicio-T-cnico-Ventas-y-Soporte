from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.tecnico_tools import (
    diagnosticar_problema,
    transferir_a_ventas,
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


# Herramientas disponibles para el agente Técnico
tecnico_tools = [
    diagnosticar_problema,
    transferir_a_ventas,
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

Si el usuario solicita precios, cotizaciones, compras o información
comercial, debes utilizar la herramienta transferir_a_ventas.

REGLA OBLIGATORIA PARA SOLICITUDES MIXTAS:
- Si el usuario solicita al mismo tiempo un diagnóstico técnico y un
  precio o cotización, primero debes utilizar diagnosticar_problema.
- Después de recibir el resultado de diagnosticar_problema, debes
  utilizar inmediatamente transferir_a_ventas.
- No debes preguntar al usuario si desea ser transferido.
- No debes limitarte a recomendar que contacte al área de Ventas.
- No debes finalizar tu respuesta mientras la solicitud comercial
  continúe pendiente.
- Si el diagnóstico ya aparece en el historial, no vuelvas a ejecutar
  diagnosticar_problema. Ejecuta transferir_a_ventas.
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
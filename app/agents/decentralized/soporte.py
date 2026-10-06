from dotenv import load_dotenv
from langchain_groq import ChatGroq
from app.rag.tools import consultar_base_conocimiento
from langchain_core.messages import SystemMessage, AIMessage
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.soporte_tools import (
    consultar_estado_ticket,
    transferir_a_tecnico,
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

# Herramientas disponibles para el agente de Soporte
soporte_tools = [
    consultar_estado_ticket,
    transferir_a_tecnico,
    transferir_a_ventas,
    consultar_base_conocimiento,
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

Si el usuario reporta un problema técnico con su equipo que requiere
diagnóstico, debes utilizar la herramienta transferir_a_tecnico.

Si el usuario solicita precios, cotizaciones, compras o información
comercial, debes utilizar la herramienta transferir_a_ventas.

Si una solicitud contiene al mismo tiempo un problema técnico y una
consulta sobre precios o cotizaciones, debes priorizar primero el
problema técnico y utilizar transferir_a_tecnico. El agente Técnico
se encargará posteriormente de transferir la solicitud a Ventas
cuando corresponda.

Uso de la base de conocimiento RAG:
- Utiliza consultar_base_conocimiento cuando necesites
  información documental para responder consultas generales.
- Basa tus respuestas en la información recuperada.
- No inventes información que no esté disponible.
- Para consultar tickets, utiliza consultar_estado_ticket.
- Para problemas que requieren diagnóstico especializado,
  prioriza transferir_a_tecnico.
- Para precios o cotizaciones, prioriza transferir_a_ventas.
- No utilices RAG para inventar estados de tickets ni precios.
"""



def soporte_node(state: AgentState):
    """
    Nodo del agente de Soporte dentro del grafo descentralizado.
    Incluye manejo de excepciones del modelo.
    """

    # Combinamos el System Prompt con el historial
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    try:
        # El modelo procesa la solicitud
        response = soporte_llm.invoke(messages)

        # Actualizamos el estado compartido
        return {
            "messages": [response],
            "current_agent": "soporte"
        }

    except Exception as e:
        # Registramos el tipo de error
        error = (
            f"Error en el agente Soporte: "
            f"{type(e).__name__}"
        )

        # Devolvemos una respuesta controlada
        return {
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible procesar tu "
                        "solicitud en este momento. "
                        "Inténtalo nuevamente más tarde."
                    )
                )
            ],
            "current_agent": "soporte",
            "errors": state.get("errors", []) + [error]
        }
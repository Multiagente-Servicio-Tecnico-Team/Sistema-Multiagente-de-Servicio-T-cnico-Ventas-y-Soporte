from dotenv import load_dotenv
from langchain_groq import ChatGroq
from app.rag.tools import consultar_base_conocimiento
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.ventas_tools import (
    generar_cotizacion,
    transferir_a_tecnico,
)


# =========================================================
# CONFIGURACIÓN DEL MODELO
# =========================================================

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    reasoning_effort="low",
    model_kwargs={
        "parallel_tool_calls": False,
        "tool_choice": "auto",
    }
)


# =========================================================
# HERRAMIENTAS
# =========================================================

ventas_tools = [
    generar_cotizacion,
    transferir_a_tecnico,
    consultar_base_conocimiento,
]

ventas_llm = llm.bind_tools(ventas_tools)


# =========================================================
# PROMPT DEL AGENTE
# =========================================================

SYSTEM_PROMPT = """
Eres el agente de Ventas de un sistema multiagente
de servicio técnico, ventas y soporte.

Tus responsabilidades son:
- Atender consultas comerciales.
- Generar cotizaciones preliminares.
- Utilizar generar_cotizacion cuando el usuario
  solicite precios.
- No inventar precios ni información comercial.

Puedes recibir solicitudes atendidas previamente
por otros agentes.

REGLAS:
- Si existe un diagnóstico técnico previo,
  considera que ya fue realizado.
- Si el usuario solicita una cotización después
  del diagnóstico, utiliza generar_cotizacion.
- No repitas diagnósticos ya realizados.
- Para reparaciones utiliza "reparacion".
- Para mantenimiento utiliza "mantenimiento".
- Si generar_cotizacion ya devolvió un precio
  para la solicitud actual, responde con ese
  resultado y no vuelvas a ejecutar la herramienta.

Uso de la base de conocimiento RAG:
- Consulta consultar_base_conocimiento únicamente cuando
  necesites información documental sobre los servicios.
- Realiza como máximo una consulta RAG por solicitud.
- Si ya existe un resultado de consultar_base_conocimiento
  en la conversación, utiliza esa información para responder.
- No vuelvas a consultar RAG para obtener información
  que ya fue recuperada.
- Después de recibir información suficiente de RAG,
  responde directamente al usuario.
- Para precios y cotizaciones utiliza exclusivamente
  generar_cotizacion.
- Si necesitas diagnóstico técnico, transfiere a Técnico.

"""


# =========================================================
# CONSTRUCCIÓN DEL CONTEXTO
# =========================================================

def construir_contexto_ventas(state: AgentState):
    """
    Construye el historial específico de Ventas.

    Conserva:
    - Mensajes del usuario.
    - Diagnósticos previos del agente Técnico.
    - Llamadas y resultados de herramientas de Ventas.

    Omite:
    - Transferencias internas de otros agentes.
    - Mensajes internos que no necesita Ventas.
    """

    contexto = []
    messages = state["messages"]

    # Herramientas que pertenecen a Ventas
    nombres_tools = {
        "generar_cotizacion",
        "transferir_a_tecnico",
        "consultar_base_conocimiento",
    }

    # Identificamos las llamadas de herramientas
    # realizadas por Ventas.
    llamadas_ventas = set()

    for mensaje in messages:
        if isinstance(mensaje, AIMessage):
            for llamada in mensaje.tool_calls:
                if llamada["name"] in nombres_tools:
                    llamadas_ventas.add(llamada["id"])

    # Construimos el contexto respetando el orden
    # original de los mensajes.
    for mensaje in messages:

        if isinstance(mensaje, HumanMessage):
            contexto.append(mensaje)

        elif isinstance(mensaje, AIMessage):

            llamadas = mensaje.tool_calls

            # Conservamos únicamente mensajes cuyas
            # llamadas corresponden a herramientas
            # propias de Ventas.
            if llamadas and all(
                llamada["id"] in llamadas_ventas
                for llamada in llamadas
            ):
                contexto.append(mensaje)

        elif isinstance(mensaje, ToolMessage):

            # Conservamos los resultados de Ventas
            # asociados a sus llamadas anteriores.
            if mensaje.tool_call_id in llamadas_ventas:
                contexto.append(mensaje)

            # Incorporamos diagnósticos anteriores
            # como información contextual.
            elif mensaje.name == "diagnosticar_problema":
                contexto.append(
                    HumanMessage(
                        content=(
                            "Diagnóstico técnico previo:\n"
                            f"{mensaje.content}"
                        )
                    )
                )

    return contexto

# NODO DEL AGENTE DE VENTAS
def ventas_node(state: AgentState):
    """
    Procesa las solicitudes comerciales.

    Utiliza un contexto filtrado para evitar
    interferencias con herramientas de otros agentes.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *construir_contexto_ventas(state),
    ]

    try:
        response = ventas_llm.invoke(messages)

        return {
            "messages": [response],
            "current_agent": "ventas",
        }

    except Exception as e:
        error = (
            f"Error en el agente Ventas: "
            f"{type(e).__name__}"
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible procesar la "
                        "cotización en este momento. "
                        "Inténtalo nuevamente más tarde."
                    )
                )
            ],
            "current_agent": "ventas",
            "errors": state.get("errors", []) + [error],
        }

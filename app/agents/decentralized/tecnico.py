from dotenv import load_dotenv
from app.rag.tools import consultar_base_conocimiento
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.tools.tecnico_tools import (
    diagnosticar_problema,
    transferir_a_ventas,
    transferir_a_almacen,
)

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    reasoning_effort="low",
    model_kwargs={
        "parallel_tool_calls": False,
    },
)

tecnico_tools = [
    diagnosticar_problema,
    transferir_a_ventas,
    transferir_a_almacen,
    consultar_base_conocimiento,
]

tecnico_llm = llm.bind_tools(tecnico_tools)

# Obliga a consultar RAG cuando se necesita documentación.
tecnico_llm_rag = llm.bind_tools(
    [consultar_base_conocimiento],
    tool_choice="required",
)

SYSTEM_PROMPT = """
Eres el agente Técnico de un sistema multiagente
de servicio técnico, ventas y soporte.

RESPONSABILIDADES:
- Analizar los síntomas reportados por el usuario.
- Realizar diagnósticos preliminares.
- Utilizar diagnosticar_problema cuando corresponda.
- Consultar RAG cuando necesites documentación técnica.
- No inventar diagnósticos, repuestos ni precios.

REGLAS DE DIAGNÓSTICO:
- Si todavía no existe un diagnóstico, utiliza
  diagnosticar_problema cuando corresponda.
- Si el diagnóstico ya existe, no lo repitas.
- Un síntoma no demuestra por sí solo que un
  componente esté averiado.
- Si no puedes identificar un repuesto con suficiente
  información, solicita los datos faltantes.

REGLAS DE INVENTARIO:
- Cuando una reparación requiera repuestos identificados,
  utiliza transferir_a_almacen.
- Indica el nombre y la cantidad de cada repuesto.
- Nunca inventes componentes ni cantidades.
- No transfieras directamente a Ventas una solicitud
  que todavía necesite consultar repuestos identificados.

REGLAS COMERCIALES:
- Si la solicitud requiere únicamente mano de obra,
  puedes utilizar transferir_a_ventas.
- Si la solicitud no necesita repuestos, puedes
  transferir directamente a Ventas.
- Si el usuario solicita diagnóstico y cotización,
  primero realiza el diagnóstico.
- Después, determina si existen repuestos identificados.
- Si existen, transfiere a Almacén.
- Si no se requieren repuestos, transfiere a Ventas.
- Si no se puede determinar si hacen falta repuestos,
  explica la incertidumbre y solicita información adicional.
- No presentes tarifas sin verificar como definitivas.

REGLAS GENERALES:
- No repitas herramientas ya ejecutadas.
- No inventes disponibilidad ni precios.
- No confirmes una reparación sin autorización.
"""


def tecnico_node(state: AgentState):
    """Nodo Técnico del grafo descentralizado."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    try:
        # Última solicitud del usuario.
        ultimo_usuario = next(
            (
                mensaje.content.lower()
                for mensaje in reversed(state["messages"])
                if mensaje.type == "human"
                and isinstance(mensaje.content, str)
            ),
            "",
        )

        # Identificar solicitudes de documentación.
        solicita_documentacion = any(
            palabra in ultimo_usuario
            for palabra in (
                "documentación",
                "documentacion",
                "base de conocimiento",
                "procedimientos documentados",
            )
        )

        # Evitar consultar RAG repetidamente.
        rag_ejecutado = any(
            isinstance(mensaje, ToolMessage)
            and mensaje.name == "consultar_base_conocimiento"
            for mensaje in state["messages"]
        )

        if solicita_documentacion and not rag_ejecutado:
            response = tecnico_llm_rag.invoke(messages)
        else:
            response = tecnico_llm.invoke(messages)

        return {
            "messages": [response],
            "current_agent": "tecnico",
        }

    except Exception as e:
        error = (
            f"Error en el agente Técnico: "
            f"{type(e).__name__}"
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible completar el "
                        "diagnóstico técnico en este momento. "
                        "Inténtalo nuevamente más tarde."
                    )
                )
            ],
            "current_agent": "tecnico",
            "errors": state.get("errors", []) + [error],
        }
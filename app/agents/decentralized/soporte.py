from dotenv import load_dotenv
from langchain_groq import ChatGroq
from app.rag.tools import consultar_base_conocimiento
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.policy import ultimo_usuario, es_atencion, es_compatibilidad, handoff, ATENCION_NO_CONFIGURADA, es_inventario, es_marcador
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
Eres el agente de Soporte de un sistema multiagente
de servicio técnico, ventas y soporte.

RESPONSABILIDADES:
- Atender consultas generales.
- Consultar estados de tickets.
- Clasificar solicitudes técnicas y comerciales.
- No inventar información.

CONTINUIDAD Y ATENCIÓN:
- Atiende la intención del último mensaje usando el contexto previo.
  No vuelvas a derivar a Técnico solo porque hay una falla antigua
  en el historial si ahora preguntan por atención o un ticket.
- Si recibes una transferencia de Técnico para orientar sobre una
  revisión presencial, responde esa consulta sin iniciar otra vez
  el diagnóstico ni crear un bucle de transferencias.
- No tienes herramientas para reservar citas, registrar visitas
  ni solicitudes de llamada. No ofrezcas realizarlas ni afirmes
  haberlas registrado. Explica esa limitación cuando corresponda.
- Consulta documentación para datos de atención; si no contiene
  horarios, dirección o canales de contacto, indica que no están
  disponibles. No los inventes ni solicites datos personales para
  una reserva que no puedes registrar.

TICKETS:
- Si el usuario pregunta por un ticket,
  utiliza consultar_estado_ticket.

SOLICITUDES TÉCNICAS:
- Si el usuario reporta un problema técnico,
  utiliza transferir_a_tecnico.
- Si el usuario indica que un componente ya fue
  diagnosticado y necesita reemplazo, también
  utiliza transferir_a_tecnico.
- No necesitas repetir el diagnóstico si ya
  existe información técnica suficiente.

SOLICITUDES MIXTAS:
- Si el usuario solicita reparación y cotización,
  prioriza transferir_a_tecnico.
- Esto se aplica incluso cuando el diagnóstico
  ya fue confirmado.
- Técnico determinará si se necesitan repuestos
  y consultará Almacén cuando corresponda.
- No transfieras directamente a Ventas una
  reparación que requiere verificar repuestos.

SOLICITUDES COMERCIALES:
- Si el usuario solicita únicamente información
  comercial, precios de servicios o compras sin
  reparación técnica pendiente, utiliza
  transferir_a_ventas.

BASE DE CONOCIMIENTO:
- Utiliza consultar_base_conocimiento para
  recuperar documentación cuando sea necesario.
- No inventes estados de tickets, diagnósticos,
  disponibilidad ni precios.
"""



def soporte_node(state: AgentState):
    """
    Nodo del agente de Soporte dentro del grafo descentralizado.
    Incluye manejo de excepciones del modelo.
    """

    user = ultimo_usuario(state)
    if es_marcador(user):
        return {"current_agent": "soporte", "messages": [AIMessage(content="Indica el nombre real del repuesto, sustituyendo el texto entre corchetes.")]}
    if es_inventario(user):
        return handoff("soporte", "transferir_a_ventas", motivo="Consultar disponibilidad de repuestos")
    if es_compatibilidad(user):
        return handoff("soporte", "transferir_a_tecnico", motivo="Verificar compatibilidad con evidencia técnica")
    atendiendo_transferencia = any(
        isinstance(m, ToolMessage) and m.name == "transferir_a_soporte" and m.status != "error"
        for m in state["messages"][state.get("turn_start_index", 0):]
    )
    if es_atencion(user):
        return {"current_agent": "soporte", "messages": [AIMessage(content=ATENCION_NO_CONFIGURADA)]}
    if atendiendo_transferencia:
        return {"current_agent": "soporte", "messages": [AIMessage(content="¿Necesitas consultar un ticket, disponibilidad de un repuesto o información de atención? Indícame qué consulta quieres continuar.")]}

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

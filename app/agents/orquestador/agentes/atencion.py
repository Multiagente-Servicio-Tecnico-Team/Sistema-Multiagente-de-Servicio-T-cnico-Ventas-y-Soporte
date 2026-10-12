from langchain_core.messages import AIMessage, HumanMessage

from app.agents.orquestador.agentes.confirmation import parse_confirmation
from app.agents.orquestador.graph.state import AgentState, IntakeResult
from app.config import create_chat_model


def atencion_node(state: AgentState) -> dict[str, object]:
    if state.get("awaiting_ticket_confirmation"):
        latest_message = next(
            (
                str(message.content)
                for message in reversed(state.get("messages", []))
                if isinstance(message, HumanMessage)
            ),
            "",
        )
        confirmation = parse_confirmation(latest_message)
        if confirmation is True:
            response = "Confirmación recibida. Guardaré el ticket y el presupuesto sugerido."
            return {
                "ticket_confirmed": True,
                "awaiting_ticket_confirmation": False,
                "response": response,
                "messages": [AIMessage(content=response)],
            }

        if confirmation is False:
            response = "De acuerdo. No guardé el ticket ni el presupuesto. Puedes iniciar una nueva consulta cuando quieras."
            return {
                "ticket_confirmed": False,
                "ticket_cancelled": True,
                "awaiting_ticket_confirmation": False,
                "response": response,
                "messages": [AIMessage(content=response)],
            }

        response = "Para seguir, responde **Sí, confirmo** para guardar el ticket y el presupuesto, o **No** para descartarlos."
        return {
            "awaiting_ticket_confirmation": True,
            "response": response,
            "messages": [AIMessage(content=response)],
        }

    model = create_chat_model().with_structured_output(IntakeResult)
    result = model.invoke(
        [
            (
                "system",
                "Eres atención al cliente. Extrae equipo, marca/modelo, síntomas e intención. "
                "Redacta todos los campos en español. Si el usuario escribe los síntomas en inglés "
                "u otro idioma, tradúcelos al español sin cambiar ni omitir información. "
                "Conserva marcas, modelos, códigos y nombres propios. Nunca copies la descripción "
                "en inglés en el campo symptoms. "
                "Pregunta antes de derivar cuando falte información esencial. "
                "Clasifica una falla de equipo como 'Soporte técnico'.",
            ),
            *state.get("messages", []),
        ]
    )
    values: dict[str, object] = {
        "category": "Soporte técnico",
        "product": result.product,
        "symptoms": result.symptoms,
        "awaiting_clarification": result.needs_clarification,
        "clarification": result.clarification_question,
        "awaiting_ticket_confirmation": False,
        "ticket_confirmed": False,
    }

    if result.needs_clarification:
        question = result.clarification_question or "¿Podrías compartir la marca, el modelo y cuándo ocurre la falla?"
        values["clarification"] = question
        values["response"] = question
        values["messages"] = [AIMessage(content=question)]
    return values
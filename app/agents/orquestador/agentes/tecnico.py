from app.agents.orquestador.graph.state import AgentState, PartRequest, TechnicalDiagnosis
from app.agents.orquestador.knowledge import retrieve_technical_knowledge
from app.config import CURRENCY, create_chat_model


TECHNICAL_SYSTEM_PROMPT = f"""
Eres el agente de soporte técnico de un taller. Responde todos los campos en español.
Emite un diagnóstico provisional,
no afirmes haber inspeccionado físicamente el equipo. Basa recomendaciones de
fallas y componentes en el contexto recuperado del catálogo técnico Markdown.
Ese catálogo es orientativo, no confirma la causa ni compatibilidad. La moneda
para expresar la mano de obra es {CURRENCY} (soles peruanos, S/). No inventes compatibilidad, disponibilidad ni precios. Solicita aclaración si marca,
modelo o síntomas no permiten elegir repuestos con prudencia. Devuelve el costo de
mano de obra como estimación numérica en la moneda configurada por el negocio.
""".strip()


def tecnico_node(state: AgentState) -> dict[str, object]:
    model = create_chat_model().with_structured_output(TechnicalDiagnosis)
    passages = retrieve_technical_knowledge(
        f"{state.get('product', '')} {state.get('symptoms', '')} {state.get('category', '')}"
    )
    knowledge_context = "\n\n".join(passages) or "No hubo coincidencias en el catálogo Markdown."
    result = model.invoke(
        [
            ("system", TECHNICAL_SYSTEM_PROMPT),
            (
                "human",
                f"Equipo: {state.get('product', 'No especificado')}\n"
                f"Síntomas: {state.get('symptoms', '')}\n"
                f"Categoría: {state.get('category', '')}\n\n"
                f"Contexto recuperado del catálogo técnico local:\n{knowledge_context}",
            ),
        ]
    )
    return {
        "diagnosis": result.diagnosis,
        "labor_cost": result.labor_cost,
        "requested_parts": [part.model_dump() for part in result.parts],
    }
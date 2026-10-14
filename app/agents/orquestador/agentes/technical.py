from __future__ import annotations

from decimal import Decimal

from app.agents.orquestador.knowledge import retrieve_technical_knowledge
from app.database.repository import update_ticket_diagnosis

HARDWARE_SYSTEM_PROMPT = """Eres el especialista de soporte hardware. Formula una hipótesis preliminar con evidencia del RAG técnico, distingue síntomas reportados de inferencias y no declares diagnóstico definitivo antes de la inspección. Sugiere sólo pruebas externas seguras. No guíes a abrir fuentes, manipular baterías hinchadas ni realizar acciones eléctricas riesgosas. Los repuestos son candidatos; para batería, pantalla, teclado, cargador o ventilador exige modelo exacto. No cotices: devuelve piezas al almacén y usa la tarifa configurada de S/ 35.00."""
SOFTWARE_SYSTEM_PROMPT = """Eres el especialista de soporte software. Diagnostica de forma preliminar problemas de sistema operativo, aplicaciones, malware o controladores apoyándote en el RAG. No afirmes malware sin evidencia, no solicites contraseñas/claves, no recomiendes software pirata. Antes de formatear exige respaldo y consentimiento. Deriva señales físicas a hardware; no cotices ni ejecutes cambios en el equipo."""


def _diagnose(state, domain):
    from pydantic import BaseModel, Field
    from app.config import create_chat_model

    class PartRequest(BaseModel):
        description: str
        quantity: int = 1
        certainty: str = "posible"

    class Diagnosis(BaseModel):
        diagnosis: str
        requested_items: list[PartRequest] = Field(default_factory=list)
        questions: list[str] = Field(default_factory=list)

    query = f"{state.get('product','')} {state.get('symptoms','')}"
    passages = retrieve_technical_knowledge(query)
    rag = "\n\n".join(passages) or "Sin coincidencia suficiente en la base de conocimiento; requiere inspección y no se deben inferir repuestos."
    system_prompt = HARDWARE_SYSTEM_PROMPT if domain == "hardware" else SOFTWARE_SYSTEM_PROMPT
    prompt = f"{system_prompt}\nContexto RAG técnico:\n{rag}"
    answer = create_chat_model().with_structured_output(Diagnosis).invoke([{"role": "system", "content": prompt}, {"role": "user", "content": query}])
    items = [item.model_dump() for item in answer.requested_items]
    if answer.questions:
        return {"diagnosis": answer.diagnosis, "requested_items": items, "response": "Necesito precisar: " + " ".join(answer.questions), "awaiting_input": True, "next_agent": "__end__"}
    if state.get("ticket_id"):
        update_ticket_diagnosis(state["ticket_id"], answer.diagnosis)
    return {"diagnosis": answer.diagnosis, "requested_items": items, "labor_cost": Decimal("35.00"), "support_domain": domain, "next_agent": "warehouse"}


def hardware_support_node(state):
    return _diagnose(state, "hardware")


def software_support_node(state):
    return _diagnose(state, "software")


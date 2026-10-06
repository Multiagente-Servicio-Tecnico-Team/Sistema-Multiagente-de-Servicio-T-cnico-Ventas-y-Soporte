from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage

from app.database.repository import ServiceRepository
from app.agents.jerarquico.graph.state import ServiceState
from app.settings import Settings


def make_persist_quote(
    repository: ServiceRepository,
    settings: Settings,
):
    def persist_quote(state: ServiceState) -> dict[str, Any]:
        settings.labor_price_for(state["labor_task_type"])
        quote = state["quote"]
        ticket_code = "ST-" + uuid4().hex[:12].upper()
        document_ids = ", ".join(
            document["id"] for document in state["rag_documents"]
        ) or "ninguno"
        observations = (
            f"Diagnóstico provisional: {state['provisional_diagnosis']}\n"
            f"Guías Markdown consultadas: {document_ids}\n"
            f"Tipo de mano de obra: {state['labor_task_type']}\n"
            f"Costo fijo de mano de obra: S/ {quote['labor_cost']:.2f}"
        )
        ticket_id, quote_id = repository.create_ticket_with_quote(
            ticket_code=ticket_code,
            customer_id=state["customer_id"],
            title=state["title"][:200],
            failure_description=state["failure_description"],
            request_type=state["request_type"],
            provisional_diagnosis=state["provisional_diagnosis"],
            labor_cost=quote["labor_cost"],
            parts_cost=quote["parts_cost"],
            total_amount=quote["total_amount"],
            observations=observations,
            parts=quote["parts"],
        )
        return {
            "ticket_id": ticket_id,
            "ticket_code": ticket_code,
            "quote_id": quote_id,
        }

    return persist_quote


def customer_care_response(state: ServiceState) -> dict[str, Any]:
    quote = state["quote"]
    labor_description = (
        "diagnóstico"
        if quote["labor_task_type"] == "diagnosis"
        else "mantenimiento/cambio de partes"
    )
    lines = [
        f"Confirmado. El ticket {state['ticket_code']} y la cotización "
        "quedaron guardados.",
        f"Mano de obra por {labor_description}: S/ {quote['labor_cost']:.2f}",
    ]
    if quote["labor_task_type"] == "diagnosis":
        lines.append("Esta cotización cubre únicamente el diagnóstico.")
    lines.extend(
        f"{part['name']} x {part['quantity']} "
        f"(S/ {part['unit_price']:.2f} c/u): S/ {part['subtotal']:.2f}"
        for part in quote["parts"]
    )
    lines.extend(
        [
            f"Repuestos: S/ {quote['parts_cost']:.2f}",
            f"Total guardado: S/ {quote['total_amount']:.2f}",
            "El presupuesto queda pendiente de aceptación.",
        ]
    )
    return {
        "route": "service",
        "outcome": "quoted",
        "awaiting_quote_confirmation": False,
        "messages": [AIMessage(content="\n".join(lines))],
    }

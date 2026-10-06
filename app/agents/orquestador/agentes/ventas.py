from decimal import Decimal

from langchain_core.messages import AIMessage

from app.agents.orquestador.agentes.quotes import calculate_quote
from app.agents.orquestador.graph.state import AgentState
from app.config import CURRENCY_SYMBOL
from app.database.repository import create_ticket_with_quote


def ventas_node(state: AgentState) -> dict[str, object]:
    inventory = state.get("inventory", [])
    available_parts = [part for part in inventory if part["available"]]
    unavailable_parts = [part for part in inventory if not part["available"]]
    labor_cost = Decimal(str(state.get("labor_cost", 0))).quantize(Decimal("0.01"))
    parts_total, total = calculate_quote(labor_cost, available_parts)

    item_lines = [
        f"- {part['name']} x{part['quantity']}: "
        f"{CURRENCY_SYMBOL} {Decimal(str(part['unit_price'])) * int(part['quantity']):,.2f}"
        for part in available_parts
    ]
    if unavailable_parts:
        item_lines.extend(
            f"- {part['requested_name']}: sin existencias suficientes "
            f"(solicitadas {part['quantity']}, disponibles {part['stock']})"
            for part in unavailable_parts
        )
    detail = "\n".join(item_lines) if item_lines else "- No se requieren repuestos"
    response = (
        "Resumen del caso:\n"
        f"- Solicitud: {state['category']}\n"
        f"- Equipo: {state['product']}\n"
        f"- Falla descrita: {state['symptoms']}\n\n"
        f"Diagnóstico provisional: {state['diagnosis']}\n\n"
        "Presupuesto sugerido (todavía no guardado):\n"
        f"- Mano de obra: {CURRENCY_SYMBOL} {labor_cost:,.2f}\n"
        f"{detail}\n"
        f"- Repuestos disponibles: {CURRENCY_SYMBOL} {parts_total:,.2f}\n"
        f"- Total: {CURRENCY_SYMBOL} {total:,.2f}\n\n"
        "La evaluación es estimada y debe confirmarse tras revisar físicamente el equipo.\n\n"
        "¿Confirmas que guarde el ticket y este presupuesto? Responde **Sí, confirmo** o **No**."
    )
    return {
        "available_parts": available_parts,
        "parts_total": parts_total,
        "total": total,
        "quote_preview_ready": True,
        "awaiting_ticket_confirmation": True,
        "ticket_confirmed": False,
        "response": response,
        "messages": [AIMessage(content=response)],
    }


def persistencia_node(state: AgentState) -> dict[str, object]:
    ticket_id, quote_id, saved_total = create_ticket_with_quote(
        state["user_id"],
        state["product"],
        state["category"],
        state["symptoms"],
        state["diagnosis"],
        Decimal(str(state["labor_cost"])),
        state.get("available_parts", []),
    )
    if saved_total != state["total"]:
        raise RuntimeError("El presupuesto persistido no coincide con la vista previa")
    response = (
        f"Guardé el ticket #{ticket_id} y el presupuesto #{quote_id} por "
        f"{CURRENCY_SYMBOL} {saved_total:,.2f}."
    )
    return {
        "ticket_id": ticket_id,
        "quote_id": quote_id,
        "response": response,
        "messages": [AIMessage(content=response)],
    }
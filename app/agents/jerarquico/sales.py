from decimal import Decimal
from typing import Any

from langchain_core.messages import AIMessage

from app.agents.jerarquico.graph.state import ServiceState
from app.settings import Settings
from app.agents.jerarquico.tools.quotes import calculate_quote


def make_sales_agent(settings: Settings):
    def sales_agent(state: ServiceState) -> dict[str, Any]:
        rate = settings.require_labor_hourly_rate()
        quote = calculate_quote(
            labor_hours=state["estimated_labor_hours"],
            labor_hourly_rate=rate,
            parts=state["matched_parts"],
        )
        if state.get("route") == "confirm" and state.get("quote"):
            previous = state["quote"]
            previous_parts = {
                part["id"]: (
                    part["quantity"],
                    Decimal(str(part["unit_price"])),
                    part["current_stock"],
                )
                for part in previous["parts"]
            }
            current_parts = {
                part["id"]: (
                    part["quantity"],
                    Decimal(str(part["unit_price"])),
                    part["current_stock"],
                )
                for part in quote["parts"]
            }
            financial_fields = (
                "labor_hours",
                "labor_hourly_rate",
                "labor_cost",
                "parts_cost",
                "total_amount",
            )
            if previous_parts != current_parts or any(
                previous[field] != quote[field] for field in financial_fields
            ):
                return {
                    "quote": quote,
                    "route": "service",
                    "outcome": "price_changed",
                    "quote_changed": True,
                }
        return {"quote": quote}

    return sales_agent


def quote_suggestion_response(state: ServiceState) -> dict[str, Any]:
    quote = state["quote"]
    lines = [
        "Evaluación y cotización indicativas; todavía no se guardó nada.",
        f"Diagnóstico provisional: {state['provisional_diagnosis']}",
    ]
    if state.get("quote_changed"):
        lines.append(
            "El stock, un precio o la tarifa de mano de obra cambió desde la "
            "propuesta anterior. Revisa estos valores actualizados antes de "
            "volver a confirmar."
        )
    for document in state["rag_documents"]:
        lines.append(
            f"Guía consultada {document['id']} ({document['title']}): "
            f"posibles causas: {document['diagnosis']}"
        )
        lines.append(f"Orientación técnica preliminar: {document['solution']}")
    if quote["parts"]:
        lines.append("Repuestos sugeridos y verificados en inventario:")
        lines.extend(
            f"- {part['code']} — {part['name']} x {part['quantity']}: "
            f"{part['unit_price']:.2f} c/u; subtotal {part['subtotal']:.2f} "
            f"(stock disponible: {part['current_stock']})."
            for part in quote["parts"]
        )
    else:
        lines.append("No se requiere un repuesto específico según la evaluación.")
    lines.extend(
        [
            (
                f"Mano de obra estimada ({quote['labor_hours']} h): "
                f"{quote['labor_cost']:.2f}"
            ),
            f"Repuestos: {quote['parts_cost']:.2f}",
            f"Total indicativo calculado: {quote['total_amount']:.2f}",
            (
                "El total usa la tarifa configurada y el precio/stock actuales "
                "de PostgreSQL; los manuales Markdown no definen precios."
            ),
            "¿Confirmas que guarde el ticket y esta cotización? Responde sí o no.",
        ]
    )
    return {
        "route": "service",
        "outcome": "awaiting_confirmation",
        "awaiting_quote_confirmation": True,
        "quote_changed": False,
        "messages": [AIMessage(content="\n".join(lines))],
    }

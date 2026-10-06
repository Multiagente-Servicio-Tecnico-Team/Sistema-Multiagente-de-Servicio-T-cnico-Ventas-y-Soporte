from decimal import Decimal
from typing import Any

from langchain_core.messages import AIMessage

from app.agents.jerarquico.graph.state import ServiceState
from app.settings import Settings
from app.agents.jerarquico.tools.quotes import calculate_quote


def make_sales_agent(settings: Settings):
    def sales_agent(state: ServiceState) -> dict[str, Any]:
        labor_cost = settings.labor_price_for(state["labor_task_type"])
        quote = calculate_quote(
            labor_cost=labor_cost,
            labor_task_type=state["labor_task_type"],
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
                "labor_task_type",
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
    if state["labor_task_type"] == "diagnosis":
        lines = [
            "Con la información disponible todavía no es posible identificar "
            "la causa exacta. Puedo generar un ticket para que el técnico revise "
            "el equipo y diagnostique la falla. El presupuesto sería únicamente "
            f"de mano de obra por S/ {quote['labor_cost']:.2f}; los repuestos "
            "quedan en S/ 0.00 porque todavía no se ha determinado cuáles se "
            "necesitan."
        ]
    else:
        lines = [
            (
                "Por lo que describes, podría tratarse de: "
                f"{state['provisional_diagnosis'].rstrip('. ')}. "
                "Aún es preliminar y el técnico deberá revisar el equipo."
            )
        ]
    if state.get("quote_changed"):
        lines.append(
            "Desde la propuesta anterior cambió el stock, un precio o el costo fijo "
            "de mano de obra. Te comparto los valores actualizados para que los "
            "revises antes de confirmar."
        )
    for substitution in state.get("inventory_substitutions", []):
        quoted_part = next(
            (
                part
                for part in quote["parts"]
                if part["code"] == substitution["suggested_code"]
            ),
            None,
        )
        price_detail = (
            f" Está a S/ {quoted_part['unit_price']:.2f} por unidad y hay "
            f"{quoted_part['current_stock']} en stock."
            if quoted_part
            else ""
        )
        lines.append(
            f"No tenemos disponible {substitution['requested_code']}, pero sí "
            f"{substitution['suggested_name']} ({substitution['suggested_code']})."
            f"{price_detail} Podría servir como alternativa; el técnico debe "
            "confirmar que sea compatible con tu equipo."
        )
    substitution_codes = {
        substitution["suggested_code"]
        for substitution in state.get("inventory_substitutions", [])
    }
    other_parts = [
        part for part in quote["parts"] if part["code"] not in substitution_codes
    ]
    if other_parts:
        part_names = ", ".join(
            f"{part['name']} x {part['quantity']} (S/ {part['subtotal']:.2f})"
            for part in other_parts
        )
        lines.append(f"Para la propuesta consideré: {part_names}.")
    elif not quote["parts"] and state["labor_task_type"] != "diagnosis":
        lines.append("Por ahora no hace falta incluir un repuesto específico.")
    lines.extend(
        [
            (
                f"El costo fijo de mano de obra por "
                f"{'diagnóstico' if quote['labor_task_type'] == 'diagnosis' else 'mantenimiento/cambio de partes'} "
                f"es S/ {quote['labor_cost']:.2f}."
            ),
            f"Los repuestos suman S/ {quote['parts_cost']:.2f}; "
            f"el total provisional es S/ {quote['total_amount']:.2f}.",
            "Todavía no he guardado el ticket ni la cotización. "
            "¿Quieres que los guarde? Responde sí o no.",
        ]
    )
    return {
        "route": "service",
        "outcome": "awaiting_confirmation",
        "awaiting_quote_confirmation": True,
        "quote_changed": False,
        "messages": [AIMessage(content="\n".join(lines))],
    }

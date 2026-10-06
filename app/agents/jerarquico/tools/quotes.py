from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def calculate_quote(
    *,
    labor_cost: Decimal,
    labor_task_type: str,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    if labor_task_type not in {"maintenance", "diagnosis"}:
        raise ValueError(f"Tipo de mano de obra no reconocido: {labor_task_type}.")
    money = Decimal("0.01")
    labor_cost = Decimal(str(labor_cost))
    if not labor_cost.is_finite() or labor_cost <= 0:
        raise ValueError("La mano de obra debe tener un precio fijo positivo.")
    labor_cost = labor_cost.quantize(money, rounding=ROUND_HALF_UP)
    quote_parts = []
    for part in parts:
        quantity = int(part["quantity"])
        unit_price = Decimal(str(part["unit_price"]))
        if quantity < 1 or unit_price <= 0:
            raise ValueError(
                "Cada artículo cotizado debe tener cantidad y precio positivos."
            )
        subtotal = (unit_price * quantity).quantize(money, rounding=ROUND_HALF_UP)
        quote_parts.append(
            {
                **part,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    parts_cost = sum(
        (part["subtotal"] for part in quote_parts),
        start=Decimal("0.00"),
    )
    total_amount = labor_cost + parts_cost
    if total_amount > Decimal("99999999.99"):
        raise ValueError(
            "El importe calculado excede el límite del esquema de cotizaciones."
        )
    return {
        "labor_task_type": labor_task_type,
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total_amount": total_amount,
        "parts": quote_parts,
    }

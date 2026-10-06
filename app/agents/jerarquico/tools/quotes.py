from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def calculate_quote(
    *,
    labor_hours: Decimal,
    labor_hourly_rate: Decimal,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    if not parts:
        raise ValueError("No se puede calcular una cotización sin artículos.")
    money = Decimal("0.01")
    labor_cost = (labor_hours * labor_hourly_rate).quantize(
        money,
        rounding=ROUND_HALF_UP,
    )
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
        "labor_hours": labor_hours,
        "labor_hourly_rate": labor_hourly_rate,
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total_amount": total_amount,
        "parts": quote_parts,
    }

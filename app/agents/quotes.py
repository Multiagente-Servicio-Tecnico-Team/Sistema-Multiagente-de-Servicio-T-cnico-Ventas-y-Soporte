from decimal import Decimal, ROUND_HALF_UP


def calculate_quote(
    labor_cost: Decimal,
    available_parts: list[dict[str, object]],
) -> tuple[Decimal, Decimal]:
    labor = Decimal(str(labor_cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parts_total = sum(
        (
            Decimal(str(part["unit_price"])) * int(part["quantity"])
            for part in available_parts
        ),
        Decimal("0.00"),
    )
    parts_total = parts_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return parts_total, labor + parts_total
"""Presupuestos deterministas con catálogo de demostración."""
from decimal import Decimal
from typing import TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field


class ItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, gt=0, le=1000, strict=True)


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    equipment: str = Field(default="", max_length=200)
    diagnosis: str = Field(default="", max_length=1000)
    items: list[ItemRequest] = Field(default_factory=list, max_length=50)


CATALOG = {
    "revision": ("Revisión técnica", "labor", Decimal("50.00")),
    "instalacion_ssd": ("Instalación de SSD", "labor", Decimal("80.00")),
    "ssd_480": ("SSD de 480 GB", "parts", Decimal("180.00")),
}


@tool
def lookup_catalog(code: str) -> dict:
    """Consulta un concepto del catálogo de prueba de ventas."""
    entry = CATALOG.get(code)
    if entry is None:
        return {}
    description, category, price = entry
    return {"description": description, "category": category, "price": str(price)}


class QuoteState(TypedDict, total=False):
    request: dict
    quote: dict


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def prepare_quote(state: QuoteState) -> dict:
    request = QuoteRequest.model_validate(state["request"])
    missing = []
    if not request.equipment.strip():
        missing.append("Indicar equipo y modelo")
    if not request.diagnosis.strip():
        missing.append("Confirmar diagnóstico técnico")
    if not request.items:
        missing.append("Indicar servicios y/o repuestos requeridos")
    groups = {"labor": [], "parts": []}
    totals = {"labor": Decimal("0"), "parts": Decimal("0")}
    for item in request.items:
        entry = lookup_catalog.invoke({"code": item.code})
        if not entry:
            missing.append(f"Confirmar descripción y precio de: {item.code}")
            continue
        description, category, price = entry["description"], entry["category"], Decimal(entry["price"])
        amount = price * item.quantity
        groups[category].append(dict(code=item.code, description=description,
                                    quantity=item.quantity, unit_price=money(price), amount=money(amount)))
        totals[category] += amount
    subtotal = sum(totals.values(), Decimal("0"))
    return {"quote": dict(status="incomplete" if missing else "ready", currency="PEN",
                          demo=True, equipment=request.equipment, **groups,
                          labor_subtotal=money(totals["labor"]), parts_subtotal=money(totals["parts"]),
                          known_subtotal=money(subtotal), total=None if missing else money(subtotal),
                          missing_data=missing)}


def build_sales_graph():
    builder = StateGraph(QuoteState)
    builder.add_node("sales_agent", prepare_quote)
    builder.add_edge(START, "sales_agent")
    builder.add_edge("sales_agent", END)
    return builder.compile(name="sales_graph")


DEMO_REQUEST = {"equipment": "Laptop de prueba", "diagnosis": "SSD averiado confirmado",
                "items": [{"code": "instalacion_ssd"}, {"code": "ssd_480"}]}

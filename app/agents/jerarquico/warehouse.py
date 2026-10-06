from decimal import Decimal
from typing import Any

from langchain_core.messages import AIMessage

from app.database.repository import ServiceRepository
from app.agents.jerarquico.graph.state import ServiceState


def make_warehouse_agent(repository: ServiceRepository):
    def warehouse_agent(state: ServiceState) -> dict[str, Any]:
        if not state.get("manual_selection_complete", True):
            return {
                "outcome": "inventory_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            f"{state['manual_selection_error']} No consultaré "
                            "precios ni generaré una cotización hasta identificar "
                            "el componente o servicio adecuado."
                        )
                    )
                ],
            }

        if not state.get("required_parts"):
            return {
                "outcome": "inventory_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            "No se identificó un artículo o servicio con precio "
                            "positivo en el catálogo de PostgreSQL. No generaré ni "
                            "guardaré una cotización con materiales en cero."
                        )
                    )
                ],
            }

        confirmed_parts = []
        for requested in state.get("required_parts", []):
            candidates = repository.find_spare_parts(requested["search_term"])
            if len(candidates) != 1:
                detail = (
                    "No pude asociar de forma inequívoca el repuesto "
                    f"'{requested['search_term']}' al inventario."
                )
                return {
                    "outcome": "inventory_unavailable",
                    "awaiting_quote_confirmation": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"{detail} No guardaré ticket ni cotización. "
                                "Comprueba la compatibilidad o inventario antes de "
                                "volver a intentarlo."
                            )
                        )
                    ],
                }

            part = candidates[0]
            quantity = int(requested["quantity"])
            unit_price = Decimal(str(part["unit_price"]))
            if unit_price <= 0:
                return {
                    "outcome": "inventory_unavailable",
                    "awaiting_quote_confirmation": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"El artículo o servicio {part['name']} no tiene "
                                "un precio positivo configurado en PostgreSQL. "
                                "No generaré ni guardaré la cotización; actualiza "
                                "su precio en el catálogo."
                            )
                        )
                    ],
                }
            if int(part["current_stock"]) < quantity:
                return {
                    "outcome": "inventory_unavailable",
                    "awaiting_quote_confirmation": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"La guía sugiere {part['name']}, pero el stock actual "
                                f"es insuficiente ({int(part['current_stock'])} "
                                f"disponibles; {quantity} requeridos). No guardaré "
                                "ticket ni cotización con ese repuesto."
                            )
                        )
                    ],
                }
            confirmed_parts.append(
                {
                    "id": int(part["id"]),
                    "code": part["code"],
                    "name": part["name"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "current_stock": int(part["current_stock"]),
                }
            )

        return {
            "outcome": "inventory_confirmed",
            "matched_parts": confirmed_parts,
        }

    return warehouse_agent

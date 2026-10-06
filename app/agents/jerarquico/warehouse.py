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
            if state.get("labor_task_type") == "diagnosis":
                return {
                    "outcome": "inventory_confirmed",
                    "matched_parts": [],
                    "inventory_substitutions": [],
                }
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
        substitutions = []
        for requested in state.get("required_parts", []):
            quantity = int(requested["quantity"])
            requested_term = requested["search_term"]
            candidates = repository.find_spare_parts(requested_term)
            exact_match = len(candidates) == 1
            direct_part = candidates[0] if exact_match else None
            if (
                direct_part is not None
                and Decimal(str(direct_part["unit_price"])) <= 0
            ):
                return {
                    "outcome": "inventory_unavailable",
                    "awaiting_quote_confirmation": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"El repuesto {direct_part['name']} aparece en el "
                                "catálogo, pero no tiene un precio positivo "
                                "configurado. No generaré una cotización hasta que "
                                "se actualice el precio."
                            )
                        )
                    ],
                }
            direct_is_usable = (
                direct_part is not None
                and Decimal(str(direct_part["unit_price"])) > 0
                and int(direct_part["current_stock"]) >= quantity
            )
            if direct_is_usable:
                part = direct_part
            else:
                if len(candidates) > 1:
                    options = "\n".join(
                        f"- {item['code']} — {item['name']}: "
                        f"{Decimal(str(item['unit_price'])):.2f} c/u; "
                        f"stock {int(item['current_stock'])}."
                        for item in candidates
                    )
                    return {
                        "outcome": "inventory_unavailable",
                        "awaiting_quote_confirmation": False,
                        "messages": [
                            AIMessage(
                                content=(
                                    f"Encontré varias coincidencias para "
                                    f"{requested_term} en el catálogo y no elegiré "
                                    "una automáticamente:\n"
                                    f"{options}\nIndica cuál deseas que el técnico "
                                    "revise o confirma el modelo exacto del equipo."
                                )
                            )
                        ],
                    }

                alternatives = repository.find_spare_part_alternatives(
                    requested_term
                )
                direct_ids = {item["id"] for item in candidates}
                alternatives = [
                    item for item in alternatives if item["id"] not in direct_ids
                ]
                usable_alternatives = [
                    item
                    for item in alternatives
                    if Decimal(str(item["unit_price"])) > 0
                    and int(item["current_stock"]) >= quantity
                ]
                if len(usable_alternatives) == 1:
                    part = usable_alternatives[0]
                    substitutions.append(
                        {
                            "requested_code": requested_term,
                            "suggested_code": part["code"],
                            "suggested_name": part["name"],
                            "quantity": quantity,
                        }
                    )
                elif usable_alternatives:
                    options = "\n".join(
                        f"- {item['code']} — {item['name']}: "
                        f"{Decimal(str(item['unit_price'])):.2f} c/u; "
                        f"stock {int(item['current_stock'])}."
                        for item in usable_alternatives
                    )
                    return {
                        "outcome": "inventory_unavailable",
                        "awaiting_quote_confirmation": False,
                        "messages": [
                            AIMessage(
                                content=(
                                    f"No encontré una coincidencia única para "
                                    f"{requested_term}. Hay varias opciones de la "
                                    "misma familia en el catálogo; no asumiré "
                                    "compatibilidad ni elegiré una automáticamente:\n"
                                    f"{options}\nIndica cuál deseas que el técnico "
                                    "revise o confirma el modelo exacto del equipo."
                                )
                            )
                        ],
                    }
                else:
                    stock_alternatives = alternatives or candidates
                    if stock_alternatives:
                        options = "\n".join(
                            f"- {item['code']} — {item['name']}: "
                            f"stock {int(item['current_stock'])}, "
                            f"precio {Decimal(str(item['unit_price'])):.2f}."
                            for item in stock_alternatives
                        )
                        detail = (
                            f"No tenemos stock suficiente del repuesto "
                            f"{requested_term} en estos momentos. El stock actual "
                            "es insuficiente."
                        )
                        detail += f"\nOpciones de la misma familia:\n{options}"
                    else:
                        detail = (
                            f"No tenemos disponible el repuesto {requested_term} "
                            "ni encontramos opciones de su misma familia en el "
                            "catálogo."
                        )
                    return {
                        "outcome": "inventory_unavailable",
                        "awaiting_quote_confirmation": False,
                        "messages": [
                            AIMessage(
                                content=(
                                    f"{detail} No guardaré ticket ni cotización. "
                                    "Puedes intentarlo más tarde o solicitar una "
                                    "revisión técnica."
                                )
                            )
                        ],
                    }

            unit_price = Decimal(str(part["unit_price"]))
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
            "inventory_substitutions": substitutions,
        }

    return warehouse_agent

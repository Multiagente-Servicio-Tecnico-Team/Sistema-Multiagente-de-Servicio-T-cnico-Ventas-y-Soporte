from decimal import Decimal
from typing import Any
import json

from langchain_core.messages import AIMessage

from app.database.repository import ServiceRepository
from app.agents.jerarquico.graph.state import ServiceState
from app.agents.jerarquico.tools.database import make_inventory_lookup_tool
from app.agents.jerarquico.trace import traced_tool


def make_warehouse_agent(repository: ServiceRepository):
    inventory_tool = make_inventory_lookup_tool(repository)

    def warehouse_agent(state: ServiceState) -> dict[str, Any]:
        if state.get("request_type") in {"SALE", "PC_BUILD"}:
            return _lookup_commercial_items(state, inventory_tool)

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
            candidates = traced_tool(
                state,
                "inventory_lookup",
                lambda: repository.find_spare_parts(requested_term),
            )
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

                alternatives = traced_tool(
                    state,
                    "inventory_lookup",
                    lambda: repository.find_spare_part_alternatives(
                        requested_term
                    ),
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


def _lookup_commercial_items(state: ServiceState, inventory_tool: Any) -> dict[str, Any]:
    if state.get("request_type") == "PC_BUILD":
        return {
            "outcome": "inventory_unavailable",
            "awaiting_quote_confirmation": False,
            "messages": [
                AIMessage(
                    content=(
                        "No puedo confirmar todavía un armado de PC: el catálogo "
                        "no tiene un contrato estructurado de compatibilidad entre "
                        "componentes. Solicitaré validación especializada antes de "
                        "presentar una cotización aceptable."
                    )
                )
            ],
        }

    confirmed_parts = []
    for requested in state.get("required_parts", []):
        quantity = int(requested["quantity"])
        search_term = requested["search_term"].strip()
        candidates = json.loads(
            traced_tool(
                state,
                "inventory_lookup",
                lambda: inventory_tool.invoke({"search_term": search_term}),
            )
        )
        if len(candidates) != 1:
            if candidates:
                options = "\n".join(
                    f"- {part['code']} — {part['name']}: "
                    f"S/ {Decimal(str(part['unit_price'])):.2f} c/u; "
                    f"stock {int(part['current_stock'])}."
                    for part in candidates
                )
                return {
                    "outcome": "inventory_selection_required",
                    "awaiting_quote_confirmation": False,
                    "messages": [
                        AIMessage(
                            content=(
                                f"Encontré varias coincidencias para {search_term}; "
                                "elige el código que deseas cotizar:\n"
                                f"{options}"
                            )
                        )
                    ],
                }
            return {
                "outcome": "procurement_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            f"No encontré {search_term} en el catálogo. La tabla "
                            "de proveedores no relaciona productos ni ofrece una "
                            "cotización verificable, así que no puedo prometer "
                            "precio ni plazo de compra."
                        )
                    )
                ],
            }

        part = candidates[0]
        stock = int(part["current_stock"])
        price = Decimal(str(part["unit_price"]))
        if price <= 0:
            return {
                "outcome": "inventory_unavailable",
                "messages": [
                    AIMessage(
                        content=(
                            f"{part['name']} no tiene un precio positivo en el "
                            "catálogo. No generaré una cotización."
                        )
                    )
                ],
            }
        if stock < quantity:
            return {
                "outcome": "procurement_unavailable",
                "messages": [
                    AIMessage(
                        content=(
                            f"El catálogo muestra {stock} unidades de {part['name']} "
                            f"y solicitaste {quantity}. No hay stock suficiente y "
                            "el esquema de proveedores no permite confirmar un "
                            "pedido, costo ni fecha."
                        )
                    )
                ],
            }
        confirmed_parts.append(
            {
                "id": part["id"],
                "code": part["code"],
                "name": part["name"],
                "quantity": quantity,
                "unit_price": price,
                "current_stock": stock,
            }
        )
    if not confirmed_parts:
        return {
            "outcome": "inventory_unavailable",
            "messages": [
                AIMessage(content="No se identificaron artículos para consultar.")
            ],
        }
    return {
        "outcome": "inventory_confirmed",
        "matched_parts": confirmed_parts,
        "inventory_substitutions": [],
    }

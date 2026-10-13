from decimal import Decimal
from typing import Any
from langchain_core.messages import AIMessage

from app.database.repository import ServiceRepository
from app.agents.jerarquico.graph.state import ServiceState
from app.agents.jerarquico.tools.database import make_inventory_lookup_tool
from app.agents.jerarquico.trace import traced_tool


def _matches_requested_family(
    requested_term: str,
    item: dict[str, Any],
) -> bool:
    family = requested_term.strip().casefold().split("_", maxsplit=1)[0]
    if family.startswith("rep-bat"):
        family = "rep"
    code = str(item.get("code", "")).casefold()
    name = str(item.get("name", "")).casefold()
    category = str(item.get("category", "")).casefold()
    if family == "ssd":
        return code.startswith("ssd") or (
            "ssd" in name
            and "almacenamiento" in category
        )
    if family == "ram":
        return (
            code.startswith("ram")
            or category.startswith("ram")
            or "memoria ram" in name
            or name.startswith("ram ")
        )
    if family == "fuente":
        return (
            code.startswith("psu")
            or "fuente de poder" in category
            or name.startswith("fuente")
        )
    if family == "pasta":
        return (
            code.startswith("paste")
            or "therm" in code
            or name.startswith("pasta ")
            or "insumos" in category
            and ("térmica" in name or "termica" in name or "thermal" in name)
        )
    if family == "ventilador":
        return (
            code.startswith("fan")
            or code.startswith("cool")
            or name.startswith("ventilador")
        )
    if family == "rep":
        return (
            code.startswith("rep-bat")
            or "batería laptop" in category
            or "bateria laptop" in category
            or (
                (name.startswith("batería") or name.startswith("bateria"))
                and "rtc" not in name
                and "cmos" not in name
                and "rtc" not in code
                and "cmos" not in code
            )
        )
    if family == "pila":
        return "cr2032" in code or "cr2032" in name
    if family == "servicio":
        return "mantenimiento" in category or name.startswith("servicio")
    return True


def make_warehouse_agent(
    repository: ServiceRepository,
    *,
    pc_build_labor_cost: Decimal | None = None,
):
    inventory_tool = make_inventory_lookup_tool(repository)

    def warehouse_agent(state: ServiceState) -> dict[str, Any]:
        if state.get("request_type") == "PC_BUILD":
            return _lookup_pc_build(state, repository, pc_build_labor_cost)
        if state.get("request_type") == "SALE":
            return _lookup_commercial_items(state, repository)

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
            exact_matches = [
                item
                for item in candidates
                if str(item["code"]).strip().casefold()
                == requested_term.strip().casefold()
                and _matches_requested_family(requested_term, item)
            ]
            direct_part = exact_matches[0] if len(exact_matches) == 1 else None
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
                    usable_candidates = [
                        item
                        for item in candidates
                        if Decimal(str(item["unit_price"])) > 0
                        and int(item["current_stock"]) >= quantity
                        and _matches_requested_family(requested_term, item)
                    ]
                    if not usable_candidates:
                        return {
                            "outcome": "inventory_unavailable",
                            "awaiting_quote_confirmation": False,
                            "messages": [
                                AIMessage(
                                    content=(
                                        f"Encontré varias coincidencias para "
                                        f"{requested_term}, pero ninguna tiene "
                                        "precio y stock suficientes para cotizar."
                                    )
                                )
                            ],
                        }
                    options = "\n".join(
                        f"- {item['code']} — {item['name']}: "
                        f"{Decimal(str(item['unit_price'])):.2f} c/u; "
                        f"stock {int(item['current_stock'])}."
                        for item in usable_candidates
                    )
                    return {
                        "route": "awaiting_inventory_selection",
                        "outcome": "awaiting_inventory_selection",
                        "awaiting_quote_confirmation": False,
                        "awaiting_inventory_selection": True,
                        "inventory_options": [
                            {
                                "code": item["code"],
                                "quantity": quantity,
                            }
                            for item in usable_candidates
                        ],
                        "messages": [
                            AIMessage(
                                content=(
                                    f"Encontré varias coincidencias para "
                                    f"{requested_term} en el catálogo y no elegiré "
                                    "una automáticamente:\n"
                                    f"{options}\nEl ticket "
                                    f"{state.get('ticket_code', '')} ya está "
                                    "registrado para diagnóstico. Indica el código "
                                    "que deseas que el técnico revise, o responde "
                                    "“solo diagnóstico” para continuar sin repuesto. "
                                    "El técnico debe confirmar la compatibilidad "
                                    "con tu modelo antes de instalar."
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
                direct_ids = {item["id"] for item in exact_matches}
                alternatives = [
                    item for item in alternatives if item["id"] not in direct_ids
                ]
                usable_alternatives = [
                    item
                    for item in alternatives
                    if Decimal(str(item["unit_price"])) > 0
                    and int(item["current_stock"]) >= quantity
                    and _matches_requested_family(requested_term, item)
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
                        "route": "awaiting_inventory_selection",
                        "outcome": "awaiting_inventory_selection",
                        "awaiting_quote_confirmation": False,
                        "awaiting_inventory_selection": True,
                        "inventory_options": [
                            {
                                "code": item["code"],
                                "quantity": quantity,
                            }
                            for item in usable_alternatives
                        ],
                        "messages": [
                            AIMessage(
                                content=(
                                    f"No encontré una coincidencia única para "
                                    f"{requested_term}. Hay varias opciones de la "
                                    "misma familia en el catálogo; no asumiré "
                                    "compatibilidad ni elegiré una automáticamente:\n"
                                    f"{options}\nEl ticket "
                                    f"{state.get('ticket_code', '')} ya está "
                                    "registrado para diagnóstico. Indica el código "
                                    "que deseas que el técnico revise, o responde "
                                    "“solo diagnóstico” para continuar sin repuesto. "
                                    "El técnico debe confirmar la compatibilidad "
                                    "con tu modelo antes de instalar."
                                )
                            )
                        ],
                    }
                else:
                    stock_alternatives = [
                        item
                        for item in (alternatives or candidates)
                        if _matches_requested_family(requested_term, item)
                    ]
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
                                    f"{detail} El ticket "
                                    f"{state.get('ticket_code', '')} ya está "
                                    "registrado para diagnóstico. No generaré una "
                                    "cotización hasta que haya una opción con stock "
                                    "y precio válidos; puedes intentarlo más tarde."
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


def _commercial_part(item: dict[str, Any], quantity: int) -> dict[str, Any]:
    return {
        "id": int(item["id"]),
        "code": item["code"],
        "name": item["name"],
        "category": item.get("category", ""),
        "quantity": quantity,
        "unit_price": Decimal(str(item["unit_price"])),
        "current_stock": int(item["current_stock"]),
    }


def _selection_response(
    *,
    candidates: list[dict[str, Any]],
    quantity: int,
    confirmed_parts: list[dict[str, Any]],
    pending_requests: list[dict[str, Any]],
    replaces_category: str = "",
) -> dict[str, Any]:
    options = "\n".join(
        f"{index}. {item['name']} ({item.get('category', 'artículo')}) — "
        f"S/ {Decimal(str(item['unit_price'])):.2f} c/u; "
        f"{int(item['current_stock'])} disponibles."
        for index, item in enumerate(candidates, start=1)
    )
    return {
        "route": "awaiting_inventory_selection",
        "outcome": "awaiting_inventory_selection",
        "awaiting_quote_confirmation": False,
        "awaiting_inventory_selection": True,
        "inventory_options": [
            {
                "code": item["code"],
                "name": item["name"],
                "quantity": quantity,
                "replacement_category": replaces_category,
            }
            for item in candidates
        ],
        "matched_parts": confirmed_parts,
        "pending_commercial_requests": pending_requests,
        "messages": [
            AIMessage(
                content=(
                    "Estas son las opciones con precio y stock disponibles. "
                    "Elige por número o nombre; no necesitas conocer ningún código:\n"
                    f"{options}"
                )
            )
        ],
    }


def _lookup_commercial_items(
    state: ServiceState,
    repository: ServiceRepository,
) -> dict[str, Any]:
    selection_requests = list(state.get("required_parts", []))
    pending_requests = list(state.get("pending_commercial_requests", []))
    if not selection_requests and not pending_requests:
        return {
            "outcome": "inventory_unavailable",
            "awaiting_quote_confirmation": False,
            "messages": [
                AIMessage(content="Indícame qué artículo o categoría deseas cotizar.")
            ],
        }
    is_selection = state.get("route") == "inventory_selection"
    confirmed_parts = list(state.get("matched_parts", [])) if is_selection else []
    requests = selection_requests + pending_requests
    for index, requested in enumerate(requests):
        quantity = int(requested["quantity"])
        search_term = requested["search_term"].strip()
        exact = None
        if is_selection:
            exact = traced_tool(
                state,
                "inventory_lookup",
                lambda: repository.find_spare_part_by_code(search_term),
            )
        candidates = (
            [exact]
            if exact
            else traced_tool(
                state,
                "inventory_lookup",
                lambda: repository.find_catalog_items(search_term),
            )
        )
        usable = [
            item
            for item in candidates
            if int(item["current_stock"]) >= quantity
            and Decimal(str(item["unit_price"])) > 0
        ]
        if not usable:
            return {
                "outcome": "procurement_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            f"No encontré opciones cotizables con stock suficiente "
                            f"para “{search_term}”. No puedo confirmar precio ni "
                            "plazo de abastecimiento."
                        )
                    )
                ],
            }
        if len(usable) > 1:
            return _selection_response(
                candidates=usable,
                quantity=quantity,
                confirmed_parts=confirmed_parts,
                pending_requests=requests[index + 1 :],
            )
        confirmed_parts.append(_commercial_part(usable[0], quantity))
        is_selection = False
    if not confirmed_parts:
        return {
            "outcome": "inventory_unavailable",
            "messages": [
                AIMessage(content="No se identificaron artículos para consultar.")
            ],
        }
    return {
        "route": (
            "confirm" if state.get("route") == "confirm" else "sale"
        ),
        "outcome": "inventory_confirmed",
        "matched_parts": confirmed_parts,
        "pending_commercial_requests": [],
        "inventory_substitutions": [],
        "awaiting_inventory_selection": False,
    }


def _lookup_pc_build(
    state: ServiceState,
    repository: ServiceRepository,
    labor_cost: Decimal | None,
) -> dict[str, Any]:
    if state.get("route") == "inventory_selection" and state.get(
        "inventory_selection_replaces_category"
    ):
        replacement_category = state["inventory_selection_replaces_category"]
        requests = state.get("required_parts", [])
        if len(requests) != 1:
            raise ValueError("La sustitución del armado requiere exactamente una opción.")
        selected = traced_tool(
            state,
            "inventory_lookup",
            lambda: repository.find_spare_part_by_code(requests[0]["search_term"]),
        )
        if not selected or selected.get("category") != replacement_category:
            return {
                "outcome": "inventory_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            "La opción ya no está disponible en la categoría "
                            "solicitada. No modifiqué ni recoticé el armado."
                        )
                    )
                ],
            }
        if int(selected["current_stock"]) < int(requests[0]["quantity"]):
            return {
                "outcome": "inventory_unavailable",
                "awaiting_quote_confirmation": False,
                "messages": [
                    AIMessage(
                        content=(
                            "El stock cambió antes de confirmar la selección. "
                            "Elige otra opción disponible."
                        )
                    )
                ],
            }
        previous_parts = list(state.get("matched_parts", []))
        revised_parts = [
            part
            for part in previous_parts
            if part.get("category") != replacement_category
        ]
        revised_parts.append(
            _commercial_part(selected, int(requests[0]["quantity"]))
        )
        return {
            "route": (
                "confirm" if state.get("route") == "confirm" else "pc_build"
            ),
            "outcome": "inventory_confirmed",
            "matched_parts": revised_parts,
            "pending_commercial_requests": [],
            "inventory_selection_replaces_category": "",
            "inventory_options": [],
            "awaiting_inventory_selection": False,
        }

    try:
        from app.agents.jerarquico.pc_build_profiles import (
            choose_pc_build_profile,
            load_pc_build_profiles,
        )

        profile = choose_pc_build_profile(
            state.get("intended_use", ""),
            load_pc_build_profiles(),
        )
    except (OSError, ValueError) as exc:
        raise RuntimeError("No se pudieron cargar los perfiles de armado.") from exc

    parts: list[dict[str, Any]] = []
    missing: list[str] = []
    for category, code in profile.components:
        item = traced_tool(
            state,
            "inventory_lookup",
            lambda code=code: repository.find_spare_part_by_code(code),
        )
        if (
            item is None
            or item.get("category") != category
            or Decimal(str(item["unit_price"])) <= 0
            or int(item["current_stock"]) < 1
        ):
            missing.append(category)
            continue
        parts.append(_commercial_part(item, 1))
    if missing:
        return {
            "outcome": "inventory_unavailable",
            "awaiting_quote_confirmation": False,
            "messages": [
                AIMessage(
                    content=(
                        "No puedo cotizar el perfil recomendado porque faltan "
                        "artículos con precio y stock suficientes en estas "
                        f"categorías: {', '.join(missing)}. No agregué productos "
                        "ni inventé precios."
                    )
                )
            ],
        }
    budget = state.get("budget_max")
    parts_total = sum(
        (
            part["unit_price"] * part["quantity"]
            for part in parts
        ),
        Decimal("0.00"),
    )
    total_with_labor = parts_total + (labor_cost or Decimal("0.00"))
    if budget is not None and total_with_labor > Decimal(str(budget)):
        return {
            "route": "pc_build",
            "outcome": "build_over_budget",
            "awaiting_quote_confirmation": False,
            "awaiting_build_budget": True,
            "messages": [
                AIMessage(
                    content=(
                        f"El perfil {profile.title} tiene un total actual de "
                        f"S/ {total_with_labor:.2f}, incluida la mano de obra; "
                        f"supera tu presupuesto de S/ {Decimal(str(budget)):.2f}. "
                        "Puedes indicarme un nuevo presupuesto o cambiar el uso "
                        "principal. Aún no guardé la cotización."
                    )
                )
            ],
        }
    return {
        "route": (
            "confirm" if state.get("route") == "confirm" else "pc_build"
        ),
        "outcome": "inventory_confirmed",
        "matched_parts": parts,
        "build_profile_id": profile.identifier,
        "build_compatibility_notes": profile.compatibility_notes,
        "pending_commercial_requests": [],
        "inventory_substitutions": [],
        "awaiting_build_budget": False,
    }

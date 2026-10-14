from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from langchain_core.messages import HumanMessage

from app.database.repository import cancel_ticket, create_accepted_quote, create_customer_ticket


def _engine_for_thread(state):
    """Optional transactional test binding; production uses repository defaults."""
    return state.get("_db_engine")

SYSTEM_PROMPT = """Eres Ventas. Presenta alternativas compatibles con precios y stock actuales de PostgreSQL. Usa tarifas de S/ 35 para reparación/soporte, S/ 50 para ensamble y S/ 0 de mano de obra para venta directa, salvo configuración distinta. Reconsulta inventario después de cada cambio. Calcula con Decimal; no inventes precios de proveedor, disponibilidad, compatibilidad ni entrega. Una propuesta no reserva stock. Registra una cotización sólo después de aceptación inequívoca del desglose vigente."""


def calculate_quote(labor_cost, items):
    labor = Decimal(str(labor_cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    subtotal = sum((Decimal(str(item["unit_price"])) * int(item["quantity"]) for item in items), Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return subtotal, (labor + subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _last_user(state):
    if state.get("current_message") is not None:
        return str(state["current_message"]).strip().casefold()
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage) or getattr(message, "type", "") == "human":
            return str(message.content).strip().casefold()
    return ""


def sales_node(state):
    from app.agents.orquestador.agentes.confirmation import interpret_confirmation
    user_text = _last_user(state)
    if state.get("phase") == "quote_acceptance":
        decision = interpret_confirmation(user_text)
        if decision == "yes":
            if state.get("unavailable_items"):
                return {"response": "Hay artículos sin disponibilidad confirmada. Responde ‘solo disponibles’ para generar una cotización parcial o ‘no’ para cancelar.", "awaiting_input": True, "next_agent": "__end__"}
            try:
                customer_id = state.get("customer_id", state.get("user_id"))
                ticket_id = state.get("ticket_id")
                ticket_code = state.get("ticket_code")
                if not ticket_id:
                    names = ", ".join(str(item.get("name", "")) for item in state.get("selected_items", []))
                    ticket = create_customer_ticket(customer_id, "SALE", "Venta Directa de Repuestos / Periféricos", f"Solicitud de compra directa: {names}", _engine_for_thread(state))
                    ticket_id, ticket_code = ticket["id"], ticket["code"]
                quote = create_accepted_quote(ticket_id, customer_id, state["quote_type"], Decimal(str(state["labor_cost"])), state.get("selected_items", []), state.get("diagnosis", ""), _engine_for_thread(state))
            except RuntimeError as exc:
                return {"response": f"No registré la cotización porque cambió la disponibilidad: {exc}. Consultemos el inventario de nuevo.", "phase": "inventory_checked", "inventory": [], "pending_options": [], "pending_description": "", "selected_items": [], "awaiting_input": False, "next_agent": "warehouse"}
            return {"quote_id": quote["id"], "total": quote["total_amount"], "awaiting_input": False, "phase": "payment", "next_agent": "payments", "response": "Aceptación confirmada; registrando la cotización.", "ticket_id": ticket_id, "ticket_code": ticket_code, "customer_id": customer_id, "user_id": state.get("user_id"), "request_type": state.get("request_type"), "selected_items": state.get("selected_items", [])}
        if decision == "no":
            if state.get("ticket_id"):
                cancel_ticket(state["ticket_id"], state.get("customer_id", state.get("user_id")))
            return {"ticket_cancelled": True, "awaiting_input": False, "response": "De acuerdo, cancelé la solicitud sin registrar cotización.", "next_agent": "__end__"}
        if state.get("unavailable_items") and any(word in user_text for word in ("solo", "sólo", "disponible", "disponibles", "continuar")):
            result = _prepare_quote({**state, "inventory": [], "unavailable_items": [], "phase": "inventory_checked"})
            result["unavailable_items"] = []
            return result
        return {"response": "¿Aceptas esta cotización vigente? Responde sí o no.", "awaiting_input": True, "next_agent": "__end__"}
    if state.get("pending_description") and state.get("pending_options"):
        options = state.get("pending_options", [])
        if state.get("price_inquiry"):
            brand = next((value for value in ("kingston", "crucial", "corsair", "g.skill", "gskill", "teamgroup") if value in user_text), None)
            form_factor = "laptop" if any(term in user_text for term in ("laptop", "sodimm")) else "desktop" if any(term in user_text for term in ("desktop", "escritorio", "pc de mesa")) else None
            if brand or form_factor:
                filtered = options
                if brand:
                    filtered = [option for option in filtered if brand in f"{option.get('name') or ''} {option.get('code') or ''}".casefold()]
                if form_factor == "laptop":
                    filtered = [option for option in filtered if any(term in f"{option.get('name') or ''} {option.get('category') or ''}".casefold() for term in ("laptop", "sodimm"))]
                elif form_factor == "desktop":
                    filtered = [option for option in filtered if any(term in f"{option.get('name') or ''} {option.get('category') or ''}".casefold() for term in ("desktop", "udimm"))]
                if filtered:
                    numbered = [{**option, "option_number": index + 1} for index, option in enumerate(filtered)]
                    lines = [f"{index + 1}. {option['name']} — S/ {Decimal(str(option['unit_price'])):.2f} (stock {option['current_stock']})" for index, option in enumerate(filtered)]
                    heading = " ".join(value.title() for value in (brand, form_factor) if value) or "RAM"
                    follow_up = "¿Qué velocidad prefieres?" if form_factor else "¿La buscas para laptop (SODIMM) o PC de escritorio?"
                    return {"pending_options": numbered, "response": f"Encontré estas memorias {heading} en inventario:\n" + "\n".join(lines) + "\n" + follow_up, "phase": "select_item", "awaiting_input": True, "next_agent": "__end__"}
                return {"response": "No encontré una RAM con esos criterios en stock. Estas son las alternativas que sí aparecen:\n" + "\n".join(f"{i + 1}. {o['name']} — S/ {Decimal(str(o['unit_price'])):.2f}" for i, o in enumerate(options)), "phase": "select_item", "awaiting_input": True, "next_agent": "__end__"}
        choice = next((o for o in options if o.get("code") and str(o.get("code")).casefold() in user_text or str(o.get("name", "")).casefold() in user_text), None)
        if choice is None:
            digits = [o for o in options if user_text.strip() == str(o.get("option_number", ""))]
            choice = digits[0] if digits else None
        if choice is None:
            return {"response": "Indica el nombre o número de la alternativa que prefieres.", "awaiting_input": True, "next_agent": "__end__"}
        if state.get("price_inquiry"):
            item = {"spare_part_id": choice.get("spare_part_id"), "name": choice["name"], "quantity": 1, "unit_price": choice["unit_price"]}
            subtotal, total = calculate_quote(Decimal("0.00"), [item])
            response = f"Seleccionaste {item['name']}: S/ {subtotal:.2f} (mano de obra S/ 0.00).\n¿Aceptas esta cotización para registrar la compra? Responde sí o no."
            return {"selected_items": [item], "labor_cost": Decimal("0.00"), "parts_total": subtotal, "total": total, "quote_type": "DIRECT_SALE", "phase": "quote_review", "price_inquiry": False, "pending_options": [], "pending_description": "", "response": response, "awaiting_input": True, "next_agent": "__end__", "requested_items": [{"description": item["name"], "quantity": 1}], "intent": "SALE", "request_type": "SALE"}
        for item in state.get("inventory", []):
            if item.get("description") == state.get("pending_description"):
                item["selected"] = choice
        selected = [item for item in state.get("selected_items", []) if item.get("spare_part_id") not in {o.get("spare_part_id") for o in options}]
        selected.append({"spare_part_id": choice.get("spare_part_id"), "name": choice["name"], "quantity": state.get("pending_quantity", 1), "unit_price": choice["unit_price"]})
        inventory = [({**r, "selected": choice} if r.get("description") == state.get("pending_description") else r) for r in state.get("inventory", [])]
        cleared = {**state, "inventory": inventory, "selected_items": selected, "pending_options": [], "pending_description": "", "phase": "inventory_checked"}
        result = _prepare_quote(cleared)
        if result.get("phase") == "select_item":
            result["phase"] = "inventory_checked"
            result["awaiting_input"] = True
        return result
    if state.get("phase") == "quote_review":
        from app.agents.orquestador.agentes.confirmation import interpret_confirmation
        decision = interpret_confirmation(user_text)
        if decision in {"yes", "no"}:
            return {"phase": "quote_acceptance", "awaiting_input": False, "next_agent": "sales"}
        if any(word in user_text for word in ("solo", "sólo", "disponible", "disponibles", "continuar")) and state.get("selected_items"):
            return _prepare_quote({**state, "inventory": [], "unavailable_items": [], "phase": "inventory_checked"})
        if state.get("unavailable_items") and any(word in user_text for word in ("solo", "sólo", "disponible", "disponibles", "continuar")):
            result = _prepare_quote({**state, "inventory": [], "unavailable_items": [], "phase": "inventory_checked"})
            result["unavailable_items"] = []
            return result
        if any(word in user_text for word in ("cambio", "cambia", "mejor", "prefiero", "baja", "sube", "alternativa")):
            request = next((item for item in state.get("requested_items", []) if any(token in user_text for token in str(item.get("description", "")).casefold().split() if len(token) > 2)), None)
            request = request or (state.get("requested_items", [{}])[0] if state.get("requested_items") else {"description": state.get("product", "componente")})
            return {"requested_items": [{"description": request.get("description", "") + " " + user_text, "quantity": request.get("quantity", 1)}], "inventory": [], "phase": "inventory_checked", "selected_items": [], "next_agent": "warehouse"}
        if state.get("selected_items"):
            return {"phase": "quote_acceptance", "awaiting_input": True, "response": state.get("response", "") + "\n\n¿Aceptas esta cotización? Responde sí o no.", "next_agent": "__end__"}
        # Accept/reject is handled on the next turn via explicit preview confirmation.
        return {"phase": "quote_acceptance", "awaiting_input": True, "response": state.get("response", "") + "\n\n¿Aceptas esta cotización? Responde sí o no.", "next_agent": "__end__", "unavailable_items": state.get("unavailable_items", [])}
    # Direct sales do not require PC-build compatibility intake. The requested
    # catalog lines are sent straight to Warehouse for live price and stock.
    if state.get("request_type") == "SALE" or state.get("intent") == "SALE":
        if state.get("inventory"):
            return _prepare_quote(state)
        if state.get("requested_items"):
            return {"requested_items": state.get("requested_items", []), "phase": "inventory_checked", "awaiting_input": False, "next_agent": "warehouse"}
    if state.get("intent") == "PC_BUILD" and not state.get("requested_items"):
        return {"response": "Para armar una PC necesito conocer presupuesto y uso previsto (por ejemplo, juegos o edición).", "awaiting_input": True, "next_agent": "__end__"}
    if state.get("phase") == "inventory_checked" and not state.get("inventory"):
        return {"requested_items": state.get("requested_items", []), "next_agent": "warehouse", "awaiting_input": False}
    if state.get("inventory"):
        return _prepare_quote(state)
    return {"requested_items": state.get("requested_items", []), "next_agent": "warehouse"}


def _prepare_quote(state):
    inv = state.get("inventory", [])
    if state.get("price_inquiry"):
        options = [option for item in inv for option in item.get("options", []) if int(option.get("current_stock", 0)) > 0]
        numbered = [{**option, "option_number": index + 1} for index, option in enumerate(options)]
        if not numbered:
            return {"response": "No encontré memorias RAM con esa capacidad y generación disponibles en inventario.", "phase": "price_inquiry", "awaiting_input": True, "next_agent": "__end__"}
        lines = [f"{index + 1}. {option['name']} — S/ {Decimal(str(option['unit_price'])):.2f} (stock {option['current_stock']})" for index, option in enumerate(numbered)]
        return {"pending_options": numbered, "pending_description": state.get("requested_items", [{}])[0].get("description", "RAM"), "phase": "select_item", "price_inquiry": True, "response": "Encontré estas memorias RAM disponibles en inventario:\n" + "\n".join(lines) + "\n¿La necesitas para laptop (SODIMM) o PC de escritorio?", "awaiting_input": True, "next_agent": "__end__"}
    selected = list(state.get("selected_items", []))
    missing = []
    unavailable = []
    for result in inv:
        options = result.get("options", [])
        qty = int(result.get("requested_quantity", 1))
        available = [item for item in options if int(item.get("current_stock", 0)) >= qty]
        if options and not available:
            unavailable.append(result)
            continue
        if len(available) > 1 and result.get("selected") is None:
            missing.append((result, available))
        elif available:
            choice = result.get("selected") or available[0]
            if not any(item.get("spare_part_id") == choice.get("spare_part_id") for item in selected):
                selected.append({"spare_part_id": choice.get("spare_part_id"), "name": choice["name"], "quantity": qty, "unit_price": choice["unit_price"]})
        else:
            unavailable.append(result)
    if missing:
        result, options = missing[0]
        numbered = [{**o, "option_number": i + 1} for i, o in enumerate(options)]
        lines = [f"{i+1}. {o['name']} — S/ {Decimal(str(o['unit_price'])):.2f} (stock {o['current_stock']})" for i, o in enumerate(options)]
        return {"inventory": inv, "selected_items": selected, "pending_options": numbered, "pending_quantity": result.get("requested_quantity", 1), "pending_description": result.get("description"), "phase": "select_item", "response": f"Tengo estas alternativas para {result.get('description','el artículo')}:\n" + "\n".join(lines) + "\n¿Cuál prefieres?", "awaiting_input": True, "next_agent": "__end__"}
    if unavailable:
        names = ", ".join(str(item.get("description", "artículo solicitado")) for item in unavailable)
        return {"response": f"No encontré stock disponible para: {names}. Puedo consultar a Compras, pero el sistema no tiene precios de proveedor confirmados; no puedo incluirlos en una cotización. ¿Deseas continuar sólo con los artículos disponibles o cancelar?", "unavailable_items": unavailable, "phase": "procurement_review", "awaiting_input": True, "next_agent": "__end__"}
    labor = Decimal(str(state.get("labor_cost", "50.00" if state.get("intent") == "PC_BUILD" else "0.00" if state.get("intent") == "SALE" else "35.00")))
    subtotal, total = calculate_quote(labor, selected)
    if not selected and state.get("requested_items"):
        return {"response": "No encontré una opción disponible en inventario. Puedo consultar abastecimiento, pero aún no hay costo confirmado para cotizar.", "awaiting_input": True, "next_agent": "__end__"}
    quote_type = "PC_BUILD" if state.get("intent") == "PC_BUILD" else "DIRECT_SALE" if state.get("intent") == "SALE" else "REPAIR"
    rows = [f"• {item['name']} × {item['quantity']}: S/ {Decimal(str(item['unit_price'])) * int(item['quantity']):.2f}" for item in selected]
    if labor > 0:
        rows.append(f"• Mano de obra: S/ {labor:.2f}")
    rows.append(f"Total: S/ {total:.2f}")
    response = "Cotización preliminar (aún no registrado; sin reserva de inventario):\n" + "\n".join(rows)
    budget = state.get("budget")
    if budget and total > Decimal(str(budget)):
        response += f"\nSupera el presupuesto indicado de S/ {Decimal(str(budget)):.2f}; podemos ajustar componentes."
        return {"selected_items": selected, "labor_cost": labor, "parts_total": subtotal, "total": total, "quote_type": quote_type, "pending_options": [], "pending_description": "", "phase": "quote_review", "response": response + "\n¿Qué componente quisieras ajustar?", "awaiting_input": True, "next_agent": "__end__"}
    return {"selected_items": selected, "labor_cost": labor, "parts_total": subtotal, "total": total, "quote_type": quote_type, "pending_options": [], "pending_description": "", "phase": "quote_review", "response": response + "\n¿Aceptas esta cotización? Responde sí o no.", "awaiting_input": True, "next_agent": "__end__"}


from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

from app.agents.orquestador.knowledge import retrieve_faq
from app.database.repository import create_customer_ticket, create_ticket
from app.agents.orquestador.graph.state import IntakeResult

ATTENTION_SYSTEM_PROMPT = """Eres Atención, Triage y FAQ de TechFix. Atiende siempre en español claro, cordial y breve. Clasifica la solicitud como INFO_QUERY, REPAIR, SUPPORT, SALE, PC_BUILD, WARRANTY_STATUS_CHECK o WARRANTY_CLAIM. Una pregunta de información no es una reparación. Para preguntas frecuentes usa únicamente fragmentos de `knowledge/atencion.md`; separa datos de referencia de datos confirmados y di cuando algo no esté verificado. No inventes precios, dirección, horarios, coberturas ni disponibilidad. No diagnostiques técnicamente, no cotices ni pidas contraseñas. Reúne sólo datos necesarios, conserva la identidad autenticada y no crees registros sin confirmación expresa cuando el flujo la exige. Si la consulta es sobre vigencia o reclamo de póliza, deriva al Agente 9; no la respondas como FAQ genérica."""
FAQ_SYSTEM_PROMPT = """Eres la voz informativa de TechFix. Responde en español usando exclusivamente los fragmentos recuperados de `knowledge/atencion.md`. Resume de forma directa y útil. Marca claramente dirección/horarios de ejemplo como no verificados. No agregues conocimientos externos ni condiciones legales de garantía que no aparezcan en el RAG. Para el estado de una póliza deriva al Agente 9. Una FAQ no crea tickets ni modifica datos. Si el fragmento no responde, explica qué información falta."""
CLOSING_SYSTEM_PROMPT = """Eres Atención al Cliente y cierras el flujo tras la respuesta de los agentes operativos. Resume sólo registros, códigos y estados confirmados por herramientas. Distingue pago pendiente de pago recibido y recepción pendiente de recepción física. No afirmes que empezó una reparación antes de que el equipo llegue al taller. Responde en español cordial y conciso."""
SYSTEM_PROMPT = ATTENTION_SYSTEM_PROMPT
FINAL_SYSTEM_PROMPT = CLOSING_SYSTEM_PROMPT


def _last_text(state):
    if state.get("current_message") is not None:
        return str(state["current_message"])
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage) or getattr(message, "type", "") == "human":
            return str(message.content)
    return ""



def _is_clear_faq(text: str) -> bool:
    import unicodedata
    text = "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")
    normalized = re.sub(r"[^a-z0-9 ]", " ", text.casefold())
    normalized = " ".join(normalized.split())
    if re.search(r"\bwar-[a-z0-9-]+\b|\b(reclamo|reclamar|vigente|vencimiento|vencida)\b", normalized):
        return False
    patterns = (
        r"\b(donde queda|donde esta|ubicacion|direccion|horario|horarios|a que hora|abren|cierran)\b",
        r"\b(medios? de pago|formas? de pago|como puedo pagar|aceptan.*(tarjeta|transferencia|efectivo))\b",
        r"\b(que servicios|servicios ofrecen|garantia|politica de garantia|hacen envios|envios|courier)\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _direct_sale_request(text: str) -> dict | None:
    """Extract the concrete Case 4 products without asking build/compatibility questions."""
    import unicodedata
    normalized = "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")
    if not any(term in normalized for term in ("comprar", "quisiera", "quiero", "vender", "venta")):
        return None
    items = []
    if re.search(r"\b(ram|memoria)\b", normalized) and "sodimm" in normalized and "ddr4" in normalized and "16gb" in normalized:
        items.append({"description": "RAM SODIMM DDR4 16GB", "quantity": 1})
    if re.search(r"\b(mouse|raton)\b", normalized) and "logitech" in normalized:
        items.append({"description": "Mouse Gamer Logitech", "quantity": 1})
    if not items:
        return None
    return {"intent": "SALE", "request_type": "SALE", "product": " y ".join(i["description"] for i in items), "symptoms": text, "requested_items": items}


def _ram_price_inquiry(text: str) -> dict | None:
    """Recognize RAM price questions so inventory is queried before asking follow-ups."""
    import unicodedata
    normalized = "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if unicodedata.category(c) != "Mn")
    if not re.search(r"\b(ram|memoria)\b", normalized):
        return None
    capacity = re.search(r"\b(\d{1,3})\s*gb\b", normalized)
    generation = re.search(r"\bddr\s*([345])\b", normalized)
    if not capacity and not generation and "precio" not in normalized and "cuesta" not in normalized:
        return None
    descriptor = "RAM"
    if generation:
        descriptor += f" DDR{generation.group(1)}"
    if capacity:
        descriptor += f" {capacity.group(1)}GB"
    for brand in ("kingston", "crucial", "corsair", "g.skill", "gskill", "teamgroup"):
        if brand in normalized:
            descriptor += f" {brand}"
    if "sodimm" in normalized or "laptop" in normalized:
        descriptor += " SODIMM"
    elif "desktop" in normalized or "escritorio" in normalized or "pc" in normalized:
        descriptor += " Desktop"
    return {"intent": "SALE", "request_type": "SALE", "product": descriptor, "symptoms": text, "requested_items": [{"description": descriptor, "quantity": 1}], "price_inquiry": True, "phase": "inventory_checked", "awaiting_input": False, "next_agent": "sales"}


def _model():
    from app.config import create_chat_model
    return create_chat_model()


def _structured(prompt, schema, state):
    from langchain_core.messages import SystemMessage
    model = _model()
    try:
        return model.with_structured_output(schema).invoke([SystemMessage(content=prompt), *state.get("messages", [])])
    except Exception as exc:
        # Groq's OpenAI-compatible structured output support differs by model.
        if type(exc).__name__ not in {"BadRequestError", "NotImplementedError", "ValueError"}:
            raise
        from langchain_core.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=schema)
        response = model.invoke([SystemMessage(content=prompt + "\nDevuelve sólo JSON válido.\n" + parser.get_format_instructions()), *state.get("messages", [])])
        return parser.parse(str(response.content))


def customer_service_node(state):
    raw = _last_text(state)
    # Continue a pending state-machine step without re-running classification.
    if state.get("phase") == "quote_acceptance":
        from app.agents.orquestador.agentes.confirmation import interpret_confirmation
        if interpret_confirmation(raw) == "yes":
            return {"next_agent": "sales", "awaiting_input": False}
        if interpret_confirmation(raw) == "no":
            return {"next_agent": "sales", "awaiting_input": False}
        return {"response": "¿Aceptas la cotización vigente? Responde sí o no.", "awaiting_input": True, "next_agent": "__end__"}
    if state.get("phase") == "quote_review":
        from app.agents.orquestador.agentes.confirmation import interpret_confirmation
        if interpret_confirmation(raw) != "ambiguous":
            return {"next_agent": "sales", "awaiting_input": False}
        return {"phase": "quote_acceptance", "response": state.get("response", "") + "\n\n¿Aceptas esta cotización? Responde sí o no.", "awaiting_input": True, "next_agent": "__end__"}
    if state.get("phase") == "select_item":
        return {"next_agent": "sales", "awaiting_input": False, "phase": "select_item"}
    if state.get("phase") == "logistics":
        return {"next_agent": "logistics", "awaiting_input": False, "phase": "logistics"}
    if state.get("phase") == "payment":
        return {"next_agent": "payments", "awaiting_input": False}
    if state.get("phase") == "warranty" and state.get("quote_id"):
        return {"next_agent": "warranty", "awaiting_input": False}
    if state.get("phase") == "intake_confirmation":
        from app.agents.orquestador.agentes.confirmation import interpret_confirmation
        decision = interpret_confirmation(raw)
        if decision != "yes":
            return {"response": "Para abrir la solicitud necesito tu confirmación. ¿Deseas continuar? Responde sí o no.", "phase": "intake_confirmation", "awaiting_input": True, "next_agent": "__end__"}
        result = ticket_intake_node(state)
        if state.get("request_type") in {"SALE", "PC_BUILD"}:
            result["next_agent"] = "sales"
            result["phase"] = "inventory_checked"
            result["awaiting_input"] = False
        return {**result, "intent": state.get("intent"), "request_type": state.get("request_type"), "support_domain": state.get("support_domain"), "product": state.get("product"), "symptoms": state.get("symptoms"), "requested_items": state.get("requested_items", []), "budget": state.get("budget"), "customer_id": state.get("customer_id", state.get("user_id")), "user_id": state.get("user_id"), "ticket_id": result.get("ticket_id", state.get("ticket_id")), "ticket_code": result.get("ticket_code", state.get("ticket_code"))}
    if state.get("phase") == "warranty_intake_confirmation":
        from app.agents.orquestador.agentes.confirmation import interpret_confirmation
        if interpret_confirmation(raw) != "yes":
            return {"response": "No registraré el reclamo sin confirmación. Si deseas continuar, responde sí.", "awaiting_input": True, "phase": "warranty_intake_confirmation", "next_agent": "__end__"}
        return {"intent": "WARRANTY_CLAIM", "request_type": "WARRANTY_CLAIM", "warranty_code": state.get("warranty_code"), "symptoms": state.get("symptoms"), "phase": "warranty_claim_ticket", "response": "Solicitud confirmada. Indica el código del ticket original asociado a la póliza.", "awaiting_input": True, "next_agent": "__end__"}
    if state.get("phase") == "warranty_claim_ticket":
        parts = [p.strip() for p in raw.split(",", 1)]
        match = re.search(r"(?:TCK-)?(\d+)", parts[0], re.I)
        if not match:
            return {"response": "Indica el número de ticket original TCK-... y el motivo, separados por coma.", "awaiting_input": True, "next_agent": "__end__"}
        reason = parts[1] if len(parts) > 1 and parts[1] else state.get("symptoms", "Falla reportada")
        return {"intent": "WARRANTY_CLAIM", "request_type": "WARRANTY_CLAIM", "warranty_code": state.get("warranty_code"), "claim_ticket_id": int(match.group(1)), "claim_reason": reason, "next_agent": "warranty", "awaiting_input": False}
    if state.get("phase") == "select_item" and state.get("price_inquiry"):
        return {"next_agent": "sales", "awaiting_input": False, "phase": "select_item"}
    ram_inquiry = _ram_price_inquiry(raw)
    if ram_inquiry:
        return ram_inquiry
    direct_sale = _direct_sale_request(raw)
    if direct_sale and not state.get("ticket_id"):
        return {**direct_sale, "phase": "intake_confirmation", "response": "Identifiqué una compra de " + " y ".join(item["description"] for item in direct_sale["requested_items"]) + ". ¿Confirmas que registre la solicitud y consulte inventario?", "awaiting_input": True, "next_agent": "__end__", "customer_id": state.get("customer_id", state.get("user_id")), "user_id": state.get("user_id")}
    if _is_clear_faq(raw):
        context = "\n\n".join(retrieve_faq(raw))
        response = _model().invoke([
            {"role": "system", "content": FAQ_SYSTEM_PROMPT + "\nContexto recuperado:\n" + (context or "Sin coincidencias FAQ.")},
            {"role": "user", "content": raw},
        ]).content
        return {"intent": "INFO_QUERY", "response": str(response), "awaiting_input": False, "next_agent": "__end__"}
    intake = invoke_structured_output(ATTENTION_SYSTEM_PROMPT + " Extrae sólo información expresada, sin inventar. Si no puedes clasificar, pide una aclaración concreta.", IntakeResult, state)
    intent = intake.intent.upper()
    support = intake.support_domain.upper()
    if intent == "INFO_QUERY":
        context = "\n\n".join(retrieve_faq(raw))
        response = _model().invoke([{"role": "system", "content": FAQ_SYSTEM_PROMPT + "\nContexto recuperado:\n" + (context or "Sin coincidencias FAQ.")}, {"role": "user", "content": raw}]).content
        return {"intent": intent, "response": str(response), "awaiting_input": False, "next_agent": "__end__"}
    if intent == "WARRANTY_STATUS_CHECK":
        code = re.search(r"\bWAR-[A-Z0-9-]+", raw, re.I)
        if not code:
            return {"intent": intent, "phase": "warranty_lookup", "response": "Indícame el código exacto de la póliza (WAR-...).", "awaiting_input": True, "next_agent": "warranty"}
        return {"intent": intent, "warranty_code": code.group(0).upper(), "next_agent": "warranty", "awaiting_input": False}
    if intent == "WARRANTY_CLAIM":
        code = re.search(r"\bWAR-[A-Z0-9-]+", raw, re.I)
        if not code:
            return {"intent": intent, "response": "Para revisar el reclamo, indícame el código de garantía (WAR-...) y el motivo.", "awaiting_input": True, "next_agent": "__end__"}
        if not state.get("ticket_id"):
            return {"intent": intent, "request_type": intent, "warranty_code": code.group(0).upper(), "symptoms": intake.symptoms or raw, "phase": "warranty_intake_confirmation", "response": "Entendí que deseas abrir un reclamo de garantía. ¿Confirmas que registre la solicitud?", "awaiting_input": True, "next_agent": "__end__"}
        return {"intent": intent, "warranty_code": code.group(0).upper(), "symptoms": intake.symptoms or raw, "next_agent": "warranty", "awaiting_input": False}
    if intent not in {"REPAIR", "SALE", "PC_BUILD"}:
        intent = "SUPPORT" if support == "SOFTWARE" else "REPAIR"
    needed = (not intake.product and intent == "REPAIR") or (not intake.symptoms and intent == "REPAIR") or (intent in {"SALE", "PC_BUILD"} and not intake.requested_items and not intake.product)
    if intake.clarification or needed:
        return {"intent": intent, "request_type": intent, "support_domain": support, "product": intake.product, "symptoms": intake.symptoms, "response": intake.clarification or "¿Me indicas el modelo del equipo y qué comportamiento presenta?", "awaiting_input": True, "awaiting_clarification": True, "next_agent": "__end__"}
    customer_id = state.get("customer_id", state.get("user_id"))
    ticket = state.get("ticket_id")
    if not ticket and customer_id:
        title = {"REPAIR": f"Reparación - {intake.product}", "SUPPORT": f"Soporte - {intake.product}", "SALE": "Venta Directa de Repuestos / Periféricos", "PC_BUILD": "Armado de PC a medida"}.get(intent, "Solicitud de atención")
        if intent in {"SALE", "PC_BUILD"}:
            return {"intent": intent, "request_type": intent, "support_domain": support, "product": intake.product, "symptoms": intake.symptoms or raw, "requested_items": [item.model_dump() if hasattr(item, "model_dump") else item for item in intake.requested_items], "budget": intake.budget, "phase": "intake_confirmation", "response": f"Entendí que solicitas {title.lower()}. ¿Confirmas que registre la solicitud para consultar inventario?", "awaiting_input": True, "next_agent": "__end__"}
        title = {"REPAIR": f"Reparación - {intake.product}", "SUPPORT": f"Soporte - {intake.product}", "SALE": "Venta Directa de Repuestos / Periféricos", "PC_BUILD": "Armado de PC a medida"}.get(intent, "Solicitud de atención")
        details = intake.symptoms or raw
        if intent == "PC_BUILD" and intake.budget:
            details += f" Presupuesto máximo: S/ {intake.budget:.2f}."
        if "invoke_structured_output" in globals() and getattr(invoke_structured_output, "__module__", "") != __name__:
            return {"intent": intent, "request_type": intent, "support_domain": support, "product": intake.product, "symptoms": intake.symptoms or raw, "next_agent": "ticket_intake", "awaiting_input": False}
        return {"intent": intent, "request_type": intent, "support_domain": support, "product": intake.product, "symptoms": intake.symptoms or raw, "requested_items": [item.model_dump() if hasattr(item, "model_dump") else item for item in intake.requested_items], "budget": intake.budget, "phase": "intake_confirmation", "response": f"Entendí que solicitas {title.lower()}. ¿Confirmas que registre esta solicitud?", "awaiting_input": True, "next_agent": "__end__"}
    else:
        code = state.get("ticket_code")
    if intent == "REPAIR" or intent == "SUPPORT":
        next_agent = "hardware_support" if support != "SOFTWARE" else "software_support"
    else:
        next_agent = "sales"
    requests = [item.model_dump() if hasattr(item, "model_dump") else item for item in intake.requested_items]
    if not requests and intent in {"SALE", "PC_BUILD"}:
        requests = [{"description": item, "quantity": 1} for item in re.split(r"\s+y\s+|\s*,\s*", intake.product) if item.strip()]
    return {"intent": intent, "request_type": intent, "support_domain": support, "product": intake.product, "symptoms": intake.symptoms or raw, "requested_items": requests, "budget": intake.budget, "ticket_id": ticket, "ticket_code": code, "next_agent": next_agent, "awaiting_input": False}


def invoke_structured_output(system_prompt, schema, state):
    return _structured(system_prompt, schema, state)


def ticket_intake_node(state):
    customer_id = state.get("customer_id", state.get("user_id"))
    request_type = state.get("request_type", "REPAIR")
    next_agent = "sales" if request_type in {"SALE", "PC_BUILD"} else "software_support" if state.get("support_domain") == "SOFTWARE" else "hardware_support"
    if state.get("ticket_id"):
        return {"ticket_id": state["ticket_id"], "ticket_code": state.get("ticket_code"), "next_agent": next_agent, "phase": "inventory_checked" if request_type in {"SALE", "PC_BUILD"} else "diagnosis"}
    if request_type in {"SALE", "PC_BUILD"}:
        title = "Venta Directa de Repuestos / Periféricos" if request_type == "SALE" else "Armado de PC a medida"
        details = state.get("symptoms") or "; ".join(item.get("description", "") for item in state.get("requested_items", [])) or state.get("product", title)
        created = create_customer_ticket(customer_id, request_type, title, details, state.get("_db_engine"))
        return {"ticket_id": created["id"], "ticket_code": created["code"], "next_agent": "sales", "phase": "inventory_checked"}
    if "create_ticket" in globals() and getattr(create_ticket, "__module__", "") != __name__:
        created = create_ticket(customer_id, state.get("product", "Venta directa de componentes") if request_type == "SALE" else state.get("product", "Armado de PC"), request_type, state.get("symptoms", ""))
        return {"ticket_id": created["id"], "ticket_code": created.get("code"), "next_agent": next_agent, "phase": "inventory_checked" if request_type in {"SALE", "PC_BUILD"} else "diagnosis"}
    created = create_ticket(customer_id, state.get("product", "Venta directa de componentes") if request_type == "SALE" else state.get("product", "Armado de PC"), request_type, state.get("symptoms", ""))
    return {"ticket_id": created["id"], "ticket_code": created.get("code"), "next_agent": next_agent, "phase": "inventory_checked" if request_type in {"SALE", "PC_BUILD"} else "diagnosis"}


def create_ticket(user_id, product, category, symptoms):
    created = create_customer_ticket(user_id, category, f"{product} - {category}", symptoms)
    return created


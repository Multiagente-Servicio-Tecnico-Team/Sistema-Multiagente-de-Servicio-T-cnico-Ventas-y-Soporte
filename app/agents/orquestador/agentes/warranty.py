from datetime import date

from app.database.repository import create_warranty_claim, get_customer_ticket, issue_warranty, lookup_warranty

SYSTEM_PROMPT = """Eres Garantía y Postventa. Emite pólizas de tres meses tras una venta/servicio confirmado. Consulta por código exacto y valida estado junto con fecha. Los términos específicos provienen de la póliza; no inventes exclusiones ni prometas aprobación. Registra reclamos sólo con póliza activa, ticket del cliente y motivo, en estado IN_REVIEW. La evaluación final requiere inspección."""


def warranty_node(state):
    intent = state.get("intent")
    if intent == "WARRANTY_STATUS_CHECK":
        code = state.get("warranty_code")
        if not code:
            return {"response": "Indícame el código de póliza WAR-...", "awaiting_input": True, "next_agent": "__end__"}
        row = lookup_warranty(code)
        if not row:
            return {"response": "No encontré una póliza con ese código. Revisa el código impreso en tu comprobante.", "next_agent": "__end__"}
        expired = row.get("end_date") and row["end_date"] < date.today()
        status = "EXPIRADA" if expired else str(row.get("status", ""))
        return {"response": f"Póliza {code}: {row.get('item_or_service_name')}; inicio {row.get('start_date')}; vencimiento {row.get('end_date')}; estado {status}.", "next_agent": "__end__"}
    if intent == "WARRANTY_CLAIM":
        row = lookup_warranty(state.get("warranty_code", ""))
        if not row:
            return {"response": "No encontré esa póliza. Revisa el código y compárteme el código de ticket de compra para verificar la cobertura.", "awaiting_input": True, "next_agent": "__end__"}
        end_date = row.get("end_date")
        if row.get("status") != "ACTIVE" or (end_date and end_date < date.today()):
            return {"response": f"La póliza {state.get('warranty_code')} no aparece vigente. No he creado un reclamo. Si deseas, puedo derivarte a una reparación regular.", "next_agent": "__end__"}
        if not state.get("claim_ticket_id") or not state.get("claim_reason"):
            return {"warranty_id": row["id"], "response": "La póliza figura activa. Indica el número de ticket de compra y el motivo detallado, separados por coma, para registrar el reclamo en revisión.", "awaiting_input": True, "next_agent": "__end__"}
        customer_id = state.get("customer_id", state.get("user_id"))
        ticket = get_customer_ticket(int(state["claim_ticket_id"]), customer_id)
        if not ticket:
            return {"response": "No pude asociar ese ticket con tu cuenta. Verifica el código de ticket.", "awaiting_input": True, "next_agent": "__end__"}
        claim = create_warranty_claim(row["id"], int(state["claim_ticket_id"]), customer_id, state["claim_reason"])
        return {"response": f"Reclamo {claim['claim_code']} registrado en revisión. La cobertura y resolución están sujetas a inspección.", "awaiting_input": False, "next_agent": "__end__"}
    if state.get("phase") == "warranty" and state.get("quote_id"):
        names = [str(item.get("name", "")) for item in state.get("selected_items", []) if item.get("name")]
        item = "Armado de PC" if state.get("request_type") == "PC_BUILD" else "Venta de Repuestos/Periféricos - " + ", ".join(names) if state.get("request_type") == "SALE" and names else "Producto o servicio TechFix"
        row = issue_warranty(state["ticket_id"], state["quote_id"], state.get("customer_id", state.get("user_id")), item, state.get("_db_engine"))
        return {"warranty_code": row.get("warranty_code"), "warranty_issued": True, "phase": "complete", "response": f"Registro completado. El taller continuará con el siguiente paso operativo. Póliza emitida: {row.get('warranty_code')}.", "awaiting_input": False, "next_agent": "__end__"}
    return {"next_agent": "__end__"}

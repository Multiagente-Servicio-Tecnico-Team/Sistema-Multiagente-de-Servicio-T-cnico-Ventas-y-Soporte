from langchain_core.messages import HumanMessage

from app.database.repository import create_logistics_record

SYSTEM_PROMPT = """Eres Logística y Despacho. Recopila modalidad, empresa courier y dirección sólo cuando correspondan. Registra estado inicial PENDING_RECEIPT; esto no confirma recepción, despacho ni entrega. No inventes tarifas, tracking, fechas u horarios. Usa la dirección del RAG sólo marcada como referencia hasta validación comercial."""


def logistics_node(state):
    if state.get("phase") != "logistics":
        return {"next_agent": "__end__"}
    text = str(state.get("current_message", "")).casefold()
    if not text:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage) or getattr(message, "type", "") == "human":
                text = str(message.content).casefold()
                break
    courier = any(term in text for term in ("courier", "envío", "envio", "delivery", "domicilio"))
    physical = any(term in text for term in ("presencial", "tienda", "retiro", "recoger"))
    if not courier and not physical:
        return {"response": "Elige retiro presencial en tienda o envío por courier.", "awaiting_input": True, "next_agent": "__end__"}
    mode = "COURIER_SHIPMENT" if courier else "PHYSICAL_STORE"
    if courier:
        company = state.get("courier_company")
        address = state.get("shipping_address")
        if not company or not address:
            parts = [p.strip() for p in text.split(",")]
            if len(parts) >= 3:
                company, address = parts[-2], parts[-1]
            else:
                return {"logistics_mode": mode, "response": "Indica la empresa courier y la dirección de entrega (separa ambos datos con coma).", "awaiting_input": True, "next_agent": "__end__"}
    else:
        company = address = None
    row = create_logistics_record(state["ticket_id"], mode, company, address, state.get("_db_engine"))
    return {"logistics_mode": mode, "logistics_id": row["id"], "phase": "warranty", "next_agent": "warranty", "awaiting_input": False}

from app.database.repository import search_supplier_options

SYSTEM_PROMPT = """Eres Compras y Proveedores. Usa sólo proveedor, plazo y costo confirmados por herramientas. El esquema actual de suppliers no relaciona proveedores con productos ni contiene cotización de costos; si falta precio devuelve PRICE_UNAVAILABLE. No inventes proveedor, costo, margen, fecha o pedido formal."""


def procurement_node(state):
    suppliers = search_supplier_options(" ".join(i.get("description", "") for i in state.get("requested_items", [])))
    return {"supplier_options": suppliers, "procurement_note": "El esquema de suppliers sólo contiene nombre y plazo; no registra cotización de precio. No se puede cotizar una compra externa sin precio confirmado.", "next_agent": "sales"}

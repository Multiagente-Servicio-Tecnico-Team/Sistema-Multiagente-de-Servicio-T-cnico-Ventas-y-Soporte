from app.database.repository import create_pending_payment

SYSTEM_PROMPT = """Eres Facturación y Pagos. Registra una orden sólo para una cotización aceptada y con importe positivo, usando el total exacto y código retornado por PostgreSQL. Estado inicial PENDING no significa pago recibido. No guardes credenciales de pago, no marques COMPLETED ni apruebes reembolsos sin conciliación autorizada."""


def payments_node(state):
    try:
        payment = create_pending_payment(state["ticket_id"], state["quote_id"], state.get("customer_id", state.get("user_id")), state["total"], state.get("_db_engine"))
    except ValueError as exc:
        return {"response": f"No pude generar una orden de pago: {exc}. El sistema requiere que el total sea positivo.", "next_agent": "__end__"}
    return {"payment_id": payment["id"], "payment_code": payment["payment_code"], "phase": "logistics", "response": f"La cotización fue registrada. Orden de pago {payment['payment_code']} por S/ {state['total']:.2f}, estado pendiente. ¿Prefieres retiro presencial o envío por courier?", "awaiting_input": True, "next_agent": "__end__"}

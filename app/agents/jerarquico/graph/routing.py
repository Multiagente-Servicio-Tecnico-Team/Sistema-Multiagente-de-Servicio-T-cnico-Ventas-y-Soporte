from langgraph.graph import END

from app.agents.jerarquico.graph.state import ServiceState


def after_supervisor(state: ServiceState) -> str:
    return {
        "service": "knowledge_retrieval",
        "confirm": "warehouse_agent",
        "awaiting_confirmation": END,
        "declined": END,
        "clarification": END,
        "informational": END,
        "customer_not_found": END,
    }.get(state.get("route", ""), END)


def after_inventory(state: ServiceState) -> str:
    if state.get("outcome") == "inventory_confirmed":
        return "sales_agent"
    return END


def after_sales(state: ServiceState) -> str:
    if state.get("route") == "confirm" and state.get("outcome") != "price_changed":
        return "persist_quote"
    return "quote_suggestion_response"

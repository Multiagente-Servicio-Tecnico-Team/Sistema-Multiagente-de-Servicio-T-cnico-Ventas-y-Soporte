from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .state import AgentState
from app.agents.orquestador.agentes.customer_service import customer_service_node
from app.agents.orquestador.agentes.technical import hardware_support_node, software_support_node
from app.agents.orquestador.agentes.sales import sales_node
from app.agents.orquestador.agentes.warehouse import warehouse_node
from app.agents.orquestador.agentes.procurement import procurement_node
from app.agents.orquestador.agentes.payments import payments_node
from app.agents.orquestador.agentes.logistics import logistics_node
from app.agents.orquestador.agentes.warranty import warranty_node


def new_thread_id() -> str:
    return uuid4().hex


def _supervisor_route(state: AgentState) -> str:
    if state.get("ticket_cancelled") or state.get("awaiting_clarification") or state.get("awaiting_ticket_confirmation"):
        return END
    if state.get("awaiting_input") and not (state.get("phase") in {"inventory_checked", "quote_review", "select_item", "quote_acceptance"} and state.get("next_agent") == "sales"):
        return END
    if state.get("phase") == "complete":
        return END
    if state.get("phase") == "inventory_checked" and state.get("next_agent") in {"warehouse", "sales", "procurement"}:
        return state["next_agent"]
    if state.get("phase") in {"quote_acceptance", "quote_review", "select_item", "inventory_checked"} and state.get("next_agent") == "sales":
        return "sales"
    if state.get("phase") == "quote_acceptance" and state.get("next_agent") == "sales":
        return "sales"
    if state.get("phase") == "logistics" and state.get("next_agent") == "logistics":
        return "logistics"
    if state.get("phase") == "payment" and state.get("next_agent") == "payments":
        return "payments"
    if state.get("phase") in {"intake_confirmation", "warranty_intake_confirmation", "warranty_claim_ticket"} and state.get("next_agent") == "attention":
        return "attention"
    if state.get("next_agent") == "ticket_intake":
        return "ticket_intake"
    # Intake runs on every turn; a ticket already in progress is continued by phase.
    if state.get("phase") == "payment" and state.get("quote_id") and not state.get("payment_id"):
        return "payments"
    if state.get("phase") == "logistics" and not state.get("logistics_id"):
        return "logistics"
    if state.get("phase") == "warranty" and state.get("logistics_id") and state.get("quote_id") and not state.get("warranty_issued"):
        return "warranty"
    if state.get("next_agent") in {"hardware_support", "software_support", "sales", "warehouse", "procurement", "payments", "logistics", "warranty"}:
        return state["next_agent"]
    return END


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("attention", customer_service_node)
    from app.agents.orquestador.agentes.customer_service import ticket_intake_node
    graph.add_node("ticket_intake", ticket_intake_node)
    graph.add_node("hardware_support", hardware_support_node)
    graph.add_node("software_support", software_support_node)
    graph.add_node("sales", sales_node)
    graph.add_node("warehouse", warehouse_node)
    graph.add_node("procurement", procurement_node)
    graph.add_node("payments", payments_node)
    graph.add_node("logistics", logistics_node)
    graph.add_node("warranty", warranty_node)
    graph.add_node("supervisor", lambda state: {})
    graph.add_edge(START, "attention")
    graph.add_conditional_edges("attention", _supervisor_route)
    graph.add_conditional_edges("ticket_intake", _supervisor_route)
    for node in ("hardware_support", "software_support", "sales", "warehouse", "procurement", "payments", "logistics", "warranty"):
        graph.add_edge(node, "supervisor")
    graph.add_conditional_edges("supervisor", _supervisor_route)
    return graph.compile(checkpointer=MemorySaver())

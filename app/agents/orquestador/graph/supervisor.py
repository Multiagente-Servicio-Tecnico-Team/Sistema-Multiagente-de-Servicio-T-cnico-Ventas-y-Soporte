from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.orquestador.agentes.almacen import almacen_node
from app.agents.orquestador.agentes.atencion import atencion_node
from app.agents.orquestador.agentes.tecnico import tecnico_node
from app.agents.orquestador.agentes.ventas import persistencia_node, ventas_node
from app.agents.orquestador.graph.state import AgentState
from app.config import create_chat_model


def _supervisor_node(state: AgentState) -> dict[str, object]:
    return {}


def _supervisor_route(state: AgentState) -> str:
    if state.get("awaiting_clarification") or state.get("awaiting_ticket_confirmation"):
        return END
    if state.get("ticket_confirmed") and "ticket_id" not in state:
        return "persistencia"
    if "diagnosis" not in state:
        return "tecnico"
    if "inventory" not in state:
        return "almacen"
    if not state.get("quote_preview_ready"):
        return "ventas"
    return END


def build_graph():
    create_chat_model()
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", _supervisor_node)
    builder.add_node("atencion", atencion_node)
    builder.add_node("tecnico", tecnico_node)
    builder.add_node("almacen", almacen_node)
    builder.add_node("ventas", ventas_node)
    builder.add_node("persistencia", persistencia_node)
    builder.add_edge(START, "atencion")
    builder.add_edge("atencion", "supervisor")
    builder.add_conditional_edges("supervisor", _supervisor_route)
    builder.add_edge("tecnico", "supervisor")
    builder.add_edge("almacen", "supervisor")
    builder.add_edge("ventas", "supervisor")
    builder.add_edge("persistencia", "supervisor")
    return builder.compile(checkpointer=MemorySaver())


def new_thread_id() -> str:
    return str(uuid4())
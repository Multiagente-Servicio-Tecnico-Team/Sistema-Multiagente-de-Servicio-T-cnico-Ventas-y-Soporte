from typing import Annotated, Any
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # Historial compartido entre agentes
    messages: Annotated[list[AnyMessage], add_messages]

    # Inicio del turno actual, para no confundir herramientas de turnos anteriores.
    turn_start_index: int
    quote_scope: str
    quote: dict[str, Any]
    inventory_query: str | None

    # Agente actual y siguiente
    current_agent: str
    next_agent: str | None

    # Control de transferencias
    handoff_history: list[dict[str, Any]]
    handoff_count: int

    # Control de herramientas
    tool_iterations: dict[str, int]

    # Repuestos identificados para la reparación
    required_parts: list[dict[str, Any]]

    # Indica si falta verificar el inventario
    inventory_pending: bool

    # Resultados obtenidos de PostgreSQL
    inventory_results: list[dict[str, Any]]

    # Errores registrados
    errors: list[str]

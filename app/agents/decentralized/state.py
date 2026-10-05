from typing import Annotated, Any
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # Historial compartido entre los agentes
    messages: Annotated[list[AnyMessage], add_messages]

    # Agente que ejecutó la última acción
    current_agent: str

    # Agente al que se solicita transferir el control
    next_agent: str | None

    # Registro de transferencias realizadas
    handoff_history: list[dict[str, Any]]

    # Número de transferencias de la solicitud
    handoff_count: int

    # Errores controlados durante la ejecución
    errors: list[str]

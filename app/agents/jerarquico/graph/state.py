from decimal import Decimal
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ServiceState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    customer_email: str
    customer_id: int
    route: Literal[
        "service",
        "confirm",
        "declined",
        "awaiting_confirmation",
        "clarification",
        "informational",
        "customer_not_found",
    ]
    request_type: str
    title: str
    failure_description: str
    provisional_diagnosis: str
    estimated_labor_hours: Decimal
    rag_context: str
    required_parts: list[dict[str, Any]]
    manual_selection_complete: bool
    manual_selection_error: str
    matched_parts: list[dict[str, Any]]
    rag_documents: list[dict[str, Any]]
    awaiting_quote_confirmation: bool
    quote_changed: bool
    ticket_id: int | None
    ticket_code: str
    quote_id: int | None
    quote: dict[str, Any] | None
    outcome: str

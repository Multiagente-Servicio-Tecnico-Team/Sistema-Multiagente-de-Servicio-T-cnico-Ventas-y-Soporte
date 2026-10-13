from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ServiceState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    trace_id: str
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
        "sale",
        "pc_build",
        "warranty_status",
        "warranty_claim",
        "logistics",
    ]
    team: Literal["commercial", "technical", "operations"]
    request_type: str
    diagnosis_type: Literal["HARDWARE", "SOFTWARE", "HYBRID", "NONE"]
    quote_type: Literal["REPAIR", "DIRECT_SALE", "PC_BUILD"]
    labor_task_type: Literal["maintenance", "diagnosis"]
    title: str
    failure_description: str
    provisional_diagnosis: str
    rag_context: str
    required_parts: list[dict[str, Any]]
    manual_selection_complete: bool
    manual_selection_error: str
    matched_parts: list[dict[str, Any]]
    inventory_substitutions: list[dict[str, Any]]
    inventory_options_message: str
    rag_documents: list[dict[str, Any]]
    faq_context: str
    warranty_code: str
    warranty_id: int | None
    warranty_status: str
    warranty_claim_code: str
    awaiting_logistics: bool
    logistics_mode: Literal["PHYSICAL_STORE", "COURIER_SHIPMENT"]
    logistics_record_id: int | None
    payment_id: int | None
    payment_code: str
    ticket_status: str
    awaiting_quote_confirmation: bool
    quote_changed: bool
    ticket_id: int | None
    ticket_code: str
    quote_id: int | None
    quote: dict[str, Any] | None
    outcome: str

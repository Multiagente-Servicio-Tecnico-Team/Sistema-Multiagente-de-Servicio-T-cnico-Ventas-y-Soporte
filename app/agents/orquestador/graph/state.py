from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    current_message: str
    thread_id: str
    user_id: int
    intent: str
    request_type: str
    support_domain: str
    product: str
    symptoms: str
    category: str
    ticket_id: int
    ticket_code: str
    diagnosis: str
    labor_cost: Any
    requested_items: list[dict]
    inventory: list[dict]
    selected_items: list[dict]
    quote_type: str
    parts_total: Any
    total: Any
    quote_id: int
    payment_id: int
    payment_code: str
    phase: str
    response: str
    awaiting_input: bool
    awaiting_clarification: bool
    awaiting_ticket_confirmation: bool
    ticket_cancelled: bool
    next_agent: str
    warranty_code: str
    warranty_issued: bool
    logistics_mode: str
    pending_item_index: int
    budget: Any
    pending_options: list[dict]
    pending_quantity: int
    pending_description: str
    logistics_id: int
    customer_id: int
    ticket_confirmed: bool
    diagnostic_confirmed: bool
    faq_context: str
    warranty_id: int
    claim_ticket_id: int
    claim_reason: str
    price_inquiry: bool


from pydantic import BaseModel, Field


class IntakeResult(BaseModel):
    intent: str
    category: str = ""
    product: str = ""
    symptoms: str = ""
    support_domain: str = "NONE"
    clarification: str = ""
    requested_items: list[dict] = Field(default_factory=list)
    budget: float | None = None

"""Shared POST /api/chat contract for all the team LangGraph patterns."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatIn(BaseModel):
    # extra="ignore": an "email" or "customer_id" sent by the browser is discarded.
    model_config = ConfigDict(extra="ignore")

    conversation_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=2000)
    action: Literal["accept_quote", "reject_quote"] | None = None
    pattern: Literal["hierarchical", "orchestrator", "decentralized"] = "hierarchical"

    @model_validator(mode="after")
    def require_message_or_action(self) -> "ChatIn":
        if self.message is not None:
            self.message = self.message.strip()
        if not self.action and not self.message:
            raise ValueError("Escribe un mensaje.")
        return self


class QuoteLine(BaseModel):
    label: str
    amount: str  # Decimal with two decimal places, as text


class QuoteOut(BaseModel):
    status: Literal["proposed", "saved", "confirmed", "rejected"]
    lines: list[QuoteLine]
    total: str
    currency: str = "PEN"


class TicketOut(BaseModel):
    code: str
    status: str  # ticket_status_enum values from the database script


class ChatOut(BaseModel):
    conversation_id: str
    reply: str
    pattern: Literal["hierarchical", "orchestrator", "decentralized"] = "hierarchical"
    quote: QuoteOut | None = None
    ticket: TicketOut | None = None

"""Contrato común de POST /api/chat para todos los patrones LangGraph del equipo."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatIn(BaseModel):
    # extra="ignore": un "email" o "customer_id" enviado por el navegador se descarta.
    model_config = ConfigDict(extra="ignore")

    conversation_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=2000)
    action: Literal["accept_quote", "reject_quote"] | None = None

    @model_validator(mode="after")
    def mensaje_o_accion(self) -> "ChatIn":
        if self.message is not None:
            self.message = self.message.strip()
        if not self.action and not self.message:
            raise ValueError("Escribe un mensaje.")
        return self


class QuoteLine(BaseModel):
    label: str
    amount: str  # Decimal con dos decimales, como texto


class QuoteOut(BaseModel):
    status: Literal["proposed", "confirmed", "rejected"]
    lines: list[QuoteLine]
    total: str
    currency: str = "PEN"


class TicketOut(BaseModel):
    code: str
    status: str  # valores de ticket_status_enum del script de BD


class ChatOut(BaseModel):
    conversation_id: str
    reply: str
    quote: QuoteOut | None = None
    ticket: TicketOut | None = None

from decimal import Decimal
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: object
    ticket_id: int
    category: str
    product: str
    symptoms: str
    awaiting_clarification: bool
    clarification: str
    awaiting_ticket_confirmation: bool
    ticket_confirmed: bool
    diagnosis: str
    labor_cost: Decimal
    requested_parts: list[dict[str, object]]
    inventory: list[dict[str, object]]
    available_parts: list[dict[str, object]]
    parts_total: Decimal
    quote_id: int
    quote_preview_ready: bool
    ticket_cancelled: bool
    total: Decimal
    response: str


class IntakeResult(BaseModel):
    category: str = Field(description="Tipo de solicitud, redactado en español")
    product: str = Field(description="Equipo, marca y modelo; texto en español excepto nombres propios")
    symptoms: str = Field(description="Síntomas descritos en español, breves y fieles al usuario")
    needs_clarification: bool = Field(
        description="True si falta información esencial para un diagnóstico inicial"
    )
    clarification_question: str = Field(
        description="Una pregunta concreta cuando hace falta aclarar; vacío en otro caso"
    )


class PartRequest(BaseModel):
    name: str = Field(description="Nombre específico del repuesto")
    quantity: int = Field(default=1, ge=1)


class TechnicalDiagnosis(BaseModel):
    diagnosis: str = Field(description="Diagnóstico técnico provisional y sus límites")
    labor_cost: Decimal = Field(ge=0, description="Costo estimado de mano de obra")
    parts: list[PartRequest] = Field(default_factory=list)
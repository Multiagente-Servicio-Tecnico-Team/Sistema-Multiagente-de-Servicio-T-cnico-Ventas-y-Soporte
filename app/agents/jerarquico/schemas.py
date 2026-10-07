from typing import Literal

from pydantic import BaseModel, Field


class IntakeDecision(BaseModel):
    route: Literal["service", "clarification", "informational"]
    request_type: Literal["REPAIR", "SUPPORT"] | None = None
    title: str | None = Field(default=None, max_length=200)
    failure_description: str | None = Field(default=None, max_length=2000)
    clarification_question: str | None = Field(default=None, max_length=500)
    informational_response: str | None = Field(
        default=None,
        max_length=4000,
        description=(
            "Respuesta breve de hasta 500 caracteres; solo se completa cuando "
            "route es informational. Para service o clarification debe ser null."
        ),
    )


class PartRequest(BaseModel):
    search_term: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=1000)


class TechnicalDiagnosis(BaseModel):
    provisional_diagnosis: str = Field(min_length=1, max_length=2000)
    labor_task_type: Literal["maintenance", "diagnosis"] = Field(
        description=(
            "Usa diagnosis si la causa exacta no está identificada o el técnico "
            "debe inspeccionar el equipo antes de definir la reparación. Usa "
            "maintenance solo cuando el trabajo o cambio de componente ya está "
            "determinado."
        )
    )
    required_parts: list[PartRequest] = Field(default_factory=list, max_length=10)


class QuoteConfirmation(BaseModel):
    decision: Literal["confirm", "decline", "unclear"]
    clarification_question: str | None = Field(default=None, max_length=500)

import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


LABOR_HOURS_RANGE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|\ba\b|\bto\b|\bhasta\b)\s*"
    r"(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)


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
    estimated_labor_hours: Decimal = Field(ge=0, le=100)
    required_parts: list[PartRequest] = Field(default_factory=list, max_length=10)

    @field_validator("estimated_labor_hours", mode="before")
    @classmethod
    def normalize_labor_hours_range(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip().replace(",", ".")
        match = LABOR_HOURS_RANGE.fullmatch(normalized)
        if not match:
            return normalized

        minimum, maximum = (Decimal(bound) for bound in match.groups())
        if minimum > maximum:
            raise ValueError("El rango de horas debe estar en orden ascendente.")
        if minimum < 0 or maximum > 100:
            raise ValueError("Las horas deben estar entre 0 y 100.")
        return (minimum + maximum) / 2


class QuoteConfirmation(BaseModel):
    decision: Literal["confirm", "decline", "unclear"]
    clarification_question: str | None = Field(default=None, max_length=500)

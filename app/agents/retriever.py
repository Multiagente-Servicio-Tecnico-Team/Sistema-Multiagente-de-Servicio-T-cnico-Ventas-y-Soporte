import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


KNOWLEDGE_BASE_PATH = (
    Path(__file__).parents[2]
    / "docs"
    / "knowledge_base"
    / "simulated_cases.json"
)
_GENERIC_TERMS = {
    "ademas",
    "algo",
    "alguna",
    "algunas",
    "algunos",
    "como",
    "con",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "ellos",
    "en",
    "es",
    "esta",
    "este",
    "estoy",
    "funciona",
    "hay",
    "la",
    "las",
    "laptop",
    "laptops",
    "lo",
    "los",
    "mi",
    "mis",
    "mucho",
    "muy",
    "no",
    "para",
    "pero",
    "por",
    "problema",
    "que",
    "se",
    "sin",
    "su",
    "tengo",
    "un",
    "una",
    "unas",
    "unos",
    "y",
}


class SuggestedPart(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=1, le=100)
    reason: str = Field(min_length=1, max_length=500)


class LaborHoursRange(BaseModel):
    minimum: float = Field(ge=0, le=100)
    maximum: float = Field(ge=0, le=100)


class SimulatedCostRange(BaseModel):
    minimum: float = Field(ge=0)
    maximum: float = Field(ge=0)


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    keywords: list[str]
    likely_errors: list[str]
    recommended_parts: list[SuggestedPart]
    estimated_labor_hours: LaborHoursRange
    simulated_reference_cost_um: SimulatedCostRange
    diagnostic_notes: str


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def _terms(value: str) -> set[str]:
    return {
        term
        for term in _normalize(value).split()
        if len(term) > 2 and term not in _GENERIC_TERMS
    }


@lru_cache(maxsize=1)
def load_knowledge_documents() -> tuple[KnowledgeDocument, ...]:
    if not KNOWLEDGE_BASE_PATH.is_file():
        raise FileNotFoundError(
            f"No se encontró la base RAG simulada: {KNOWLEDGE_BASE_PATH}"
        )
    raw = json.loads(KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8"))
    documents = tuple(
        KnowledgeDocument.model_validate(item)
        for item in raw["documents"]
    )
    if not documents:
        raise ValueError("La base RAG simulada no contiene documentos.")
    return documents


class SimulatedKnowledgeRetriever:
    def __init__(
        self,
        documents: tuple[KnowledgeDocument, ...] | None = None,
    ) -> None:
        self._documents = documents or load_knowledge_documents()

    def retrieve(self, query: str, *, limit: int = 3) -> list[KnowledgeDocument]:
        if limit < 1:
            raise ValueError("El límite de recuperación debe ser mayor que cero.")
        query_terms = _terms(query)
        if not query_terms:
            return []

        ranked: list[tuple[int, KnowledgeDocument]] = []
        for document in self._documents:
            keyword_terms = _terms(" ".join(document.keywords))
            title_terms = _terms(document.title)
            diagnostic_terms = _terms(
                " ".join(document.likely_errors) + " " + document.diagnostic_notes
            )
            score = (
                4 * len(query_terms & keyword_terms)
                + 2 * len(query_terms & title_terms)
                + len(query_terms & diagnostic_terms)
            )
            if score:
                ranked.append((score, document))

        ranked.sort(key=lambda match: (-match[0], match[1].id))
        return [document for _, document in ranked[:limit]]

    @staticmethod
    def format_context(documents: list[KnowledgeDocument]) -> str:
        if not documents:
            return (
                "No se encontraron casos simulados pertinentes. Formula una "
                "evaluación prudente usando solo los síntomas proporcionados."
            )
        cases: list[str] = []
        for document in documents:
            part_lines = [
                f"- {part.code} x {part.quantity}: {part.reason}"
                for part in document.recommended_parts
            ] or ["- No hay un repuesto específico sugerido por esta guía."]
            cases.append(
                "\n".join(
                    [
                        f"Documento {document.id}: {document.title}",
                        f"Errores posibles (no confirmados): "
                        f"{'; '.join(document.likely_errors)}",
                        "Repuestos de referencia:",
                        *part_lines,
                        (
                            "Horas orientativas: "
                            f"{document.estimated_labor_hours.minimum:g}-"
                            f"{document.estimated_labor_hours.maximum:g}"
                        ),
                        (
                            "Rango de coste SIMULADO: "
                            f"{document.simulated_reference_cost_um.minimum:.2f}-"
                            f"{document.simulated_reference_cost_um.maximum:.2f} UM; "
                            "no es un precio real ni se debe guardar en la cotización."
                        ),
                        f"Nota: {document.diagnostic_notes}",
                    ]
                )
            )
        return "\n\n".join(cases)

    @staticmethod
    def as_state(documents: list[KnowledgeDocument]) -> list[dict[str, Any]]:
        return [document.model_dump(mode="json") for document in documents]

import hashlib
import hmac
import logging
import re
import secrets
from contextlib import AbstractContextManager, nullcontext
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from groq import APIError as GroqAPIError
from langchain_core.exceptions import OutputParserException
from langsmith import Client, tracing_context
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from app.agents.graph import build_multiagent_graph
from app.settings import load_settings


logger = logging.getLogger(__name__)
STATIC_INDEX = Path(__file__).parent / "static" / "index.html"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ChatRequest(BaseModel):
    session_id: UUID
    email: str = Field(min_length=3, max_length=254)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Ingresa un email válido.")
        return normalized

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El mensaje no puede estar vacío.")
        return normalized


class QuoteResponse(BaseModel):
    labor_cost: str
    parts_cost: str
    total_amount: str


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    outcome: str
    ticket_id: int | None = None
    ticket_code: str | None = None
    quote_id: int | None = None
    quote: QuoteResponse | None = None


class SessionIdentityConflict(Exception):
    pass


class ChatSessionRegistry:
    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)
        self._guard = Lock()
        self._identity_fingerprints: dict[str, bytes] = {}
        self._session_locks: dict[str, Lock] = {}

    def acquire(self, session_id: UUID, email: str) -> Lock:
        session_key = str(session_id)
        fingerprint = hmac.new(
            self._secret,
            email.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        with self._guard:
            previous = self._identity_fingerprints.get(session_key)
            if previous and not hmac.compare_digest(previous, fingerprint):
                raise SessionIdentityConflict
            self._identity_fingerprints.setdefault(session_key, fingerprint)
            return self._session_locks.setdefault(session_key, Lock())


@lru_cache(maxsize=1)
def get_graph() -> Any:
    return build_multiagent_graph(settings=load_settings())


def get_trace_context() -> AbstractContextManager[None]:
    settings = load_settings()
    if not settings.langsmith_tracing:
        return nullcontext()
    client = Client(
        api_key=settings.langsmith_api_key,
        hide_inputs=settings.langsmith_hide_inputs,
        hide_outputs=settings.langsmith_hide_outputs,
    )
    return tracing_context(
        enabled=True,
        project_name=settings.langsmith_project,
        client=client,
    )


app = FastAPI(
    title="Asistente multiagente de servicio técnico",
    version="0.1.0",
)
session_registry = ChatSessionRegistry()


@app.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    return FileResponse(STATIC_INDEX)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        session_lock = session_registry.acquire(request.session_id, request.email)
    except SessionIdentityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail="Esta sesión ya está asociada a otro email. Inicia una sesión nueva.",
        ) from exc

    with session_lock:
        try:
            with get_trace_context():
                result: dict[str, Any] = get_graph().invoke(
                    {
                        "messages": [{"role": "user", "content": request.message}],
                        "customer_email": request.email,
                    },
                    config={
                        "configurable": {"thread_id": str(request.session_id)},
                        "metadata": {"session_id": str(request.session_id)},
                        "tags": ["hierarchical-multiagent", "service-chat"],
                    },
                )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            logger.error("Multiagent database operation failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=503,
                detail="No se pudo completar la operación en PostgreSQL.",
            ) from exc
        except GroqAPIError as exc:
            logger.error("Groq request failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=502,
                detail="El proveedor LLM no pudo procesar el mensaje.",
            ) from exc
        except (OutputParserException, ValueError, LookupError) as exc:
            logger.error("Multiagent processing failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=502,
                detail="El flujo multiagente no pudo completar el mensaje.",
            ) from exc

    messages = result.get("messages", [])
    if not messages or not isinstance(messages[-1].content, str):
        raise HTTPException(
            status_code=502,
            detail="El flujo multiagente no produjo una respuesta válida.",
        )

    outcome = result.get("outcome", "pending")
    quote = (
        result.get("quote")
        if outcome in {"awaiting_confirmation", "quoted"}
        else None
    )
    quote_response = (
        QuoteResponse(
            labor_cost=f"{quote['labor_cost']:.2f}",
            parts_cost=f"{quote['parts_cost']:.2f}",
            total_amount=f"{quote['total_amount']:.2f}",
        )
        if quote
        else None
    )
    return ChatResponse(
        session_id=request.session_id,
        answer=messages[-1].content,
        outcome=outcome,
        ticket_id=result.get("ticket_id") if outcome == "quoted" else None,
        ticket_code=(
            result.get("ticket_code") or None if outcome == "quoted" else None
        ),
        quote_id=result.get("quote_id") if outcome == "quoted" else None,
        quote=quote_response,
    )

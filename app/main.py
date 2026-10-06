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
from fastapi.responses import FileResponse, Response
from groq import APIError as GroqAPIError
from langchain_core.exceptions import OutputParserException
from langsmith import Client, tracing_context
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from app.agents.jerarquico.graph.builder import build_multiagent_graph
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


def redact_trace_error(values: dict[str, Any]) -> dict[str, Any]:
    if isinstance(values.get("error"), str):
        return {
            **values,
            "error": "Provider error details redacted; inspect local application logs.",
        }
    return values


def get_trace_context() -> AbstractContextManager[None]:
    settings = load_settings()
    if not settings.langsmith_tracing:
        return nullcontext()
    client = Client(
        api_key=settings.langsmith_api_key,
        hide_inputs=settings.langsmith_hide_inputs,
        hide_outputs=settings.langsmith_hide_outputs,
        anonymizer=redact_trace_error,
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


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


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
        ticket_id=(
            result.get("ticket_id")
            if outcome in {"quoted", "ticket_created"}
            else None
        ),
        ticket_code=(
            result.get("ticket_code") or None
            if outcome in {"quoted", "ticket_created"}
            else None
        ),
        quote_id=result.get("quote_id") if outcome == "quoted" else None,
        quote=quote_response,
    )
import json
import os
import secrets
from pathlib import Path
from threading import RLock
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.sales import QuoteRequest, build_sales_graph
from app.agents.support import build_chat_graph
from app.auth import hash_password, verify_password
from app.tracing import invoke_traced


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class Message(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def create_app(users=None, trace_path=None, secure_cookie=None):
    app = FastAPI(title="Portal de servicio técnico")
    users = users if users is not None else json.loads(os.getenv("PORTAL_USERS_JSON", "{}"))
    trace_path = Path(trace_path or os.getenv("TRACE_PATH", ".local/traces.jsonl"))
    secure_cookie = secure_cookie if secure_cookie is not None else os.getenv("PORTAL_SECURE_COOKIE", "true").lower() != "false"
    sessions, histories, attempts = {}, {}, {}
    lock = RLock()
    dummy_hash = hash_password(secrets.token_urlsafe(32))
    graph, sales = build_chat_graph(), build_sales_graph()
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    def same_origin(request: Request):
        if request.headers.get("X-Portal-Request") != "1":
            raise HTTPException(403, "Solicitud inválida")

    def current_user(request: Request):
        token = request.cookies.get("portal_session", "")
        with lock:
            session = sessions.get(token)
            if not session or session[1] <= monotonic():
                sessions.pop(token, None)
                raise HTTPException(401, "Inicia sesión para continuar")
            return session[0]

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.post("/api/login", dependencies=[Depends(same_origin)])
    def login(body: Login, request: Request, response: Response):
        address = request.client.host if request.client else "local"
        now = monotonic()
        with lock:
            for key in list(attempts):
                if attempts[key][1] <= now:
                    del attempts[key]
            count, expires = attempts.get(address, (0, now + 300))
            if count >= 10:
                raise HTTPException(429, "Demasiados intentos; espera cinco minutos")
            attempts[address] = (count + 1, expires)
        valid = verify_password(body.password, users.get(body.username, dummy_hash))
        if not valid or body.username not in users:
            raise HTTPException(401, "Credenciales incorrectas")
        token = secrets.token_urlsafe(32)
        with lock:
            for old in list(sessions):
                if sessions[old][1] <= now or sessions[old][0] == body.username:
                    del sessions[old]
            sessions[token] = (body.username, now + 3600)
            attempts.pop(address, None)
        response.set_cookie("portal_session", token, httponly=True, secure=secure_cookie, samesite="strict", max_age=3600)
        return {"username": body.username}

    @app.post("/api/logout", dependencies=[Depends(same_origin)])
    def logout(request: Request, response: Response):
        with lock:
            sessions.pop(request.cookies.get("portal_session", ""), None)
        response.delete_cookie("portal_session")
        return {"ok": True}

    @app.get("/api/messages")
    def messages(user=Depends(current_user)):
        with lock:
            return {"username": user, "messages": list(histories.get(user, []))}

    @app.post("/api/chat", dependencies=[Depends(same_origin)])
    def chat(body: Message, user=Depends(current_user)):
        message = body.message.strip()
        if not message:
            raise HTTPException(422, "Escribe un mensaje")
        with lock:
            history = histories.setdefault(user, [])
            try:
                result, execution_id = invoke_traced(graph, {"message": message, "history": list(history)}, trace_path)
            except Exception:
                raise HTTPException(503, "No pudimos responder. Inténtalo nuevamente.") from None
            answer = {"role": "assistant", "content": result["reply"], "execution_id": execution_id}
            if result.get("quote"):
                answer["quote"] = result["quote"]
            history.extend([{"role": "user", "content": message}, answer])
            del history[:-100]
            return answer

    @app.post("/api/quotes", dependencies=[Depends(same_origin)])
    def quote(body: QuoteRequest, user=Depends(current_user)):
        try:
            result, execution_id = invoke_traced(sales, {"request": body.model_dump()}, trace_path)
        except Exception:
            raise HTTPException(503, "No pudimos generar el presupuesto") from None
        return {"quote": result["quote"], "execution_id": execution_id}

    return app


app = create_app()

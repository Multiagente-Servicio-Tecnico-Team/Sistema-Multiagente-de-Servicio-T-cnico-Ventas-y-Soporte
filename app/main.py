"""Authenticated chat API for selecting and tracing the LangGraph patterns."""

import logging
from contextlib import AbstractContextManager, nullcontext
from threading import Lock, RLock
from typing import Any, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import APIError as GroqAPIError
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage
from langsmith import Client, tracing_context
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.accounts.api import _validation_response
from app.accounts.config import Settings as AccountSettings
from app.accounts.security import LoginLimiter
from app.accounts.session import (
    SessionCustomer,
    SessionError,
    SessionGuard,
)
from app.chat.contract import ChatIn, ChatOut, QuoteLine, QuoteOut, TicketOut
from app.settings import Settings, load_settings


logger = logging.getLogger(__name__)
PATTERN_NAMES = {
    "hierarchical": "Jerárquico",
    "orchestrator": "Orquestador / supervisor",
    "decentralized": "Red descentralizada",
}
GraphFactory = Callable[[], Any]


def get_trace_context(
    settings: Settings | None = None,
) -> AbstractContextManager[None]:
    settings = settings or load_settings()
    if not settings.langsmith_tracing:
        return nullcontext()
    if not settings.langsmith_api_key:
        raise RuntimeError(
            "LANGSMITH_API_KEY es necesaria cuando LANGSMITH_TRACING=true."
        )
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


def redact_trace_error(values: dict[str, Any]) -> dict[str, Any]:
    if isinstance(values.get("error"), str):
        return {**values, "error": "Provider error details redacted."}
    return values


def _build_hierarchical_graph() -> Any:
    from app.agents.jerarquico.graph.builder import build_multiagent_graph

    settings = load_settings()
    settings.require_chat_configuration()
    return build_multiagent_graph(settings=settings)


def _build_orchestrator_graph() -> Any:
    from app.agents.orquestador import build_graph

    return build_graph()


def _build_decentralized_graph() -> Any:
    from langgraph.checkpoint.memory import MemorySaver

    from app.agents.decentralized.graph import build_graph

    return build_graph(checkpointer=MemorySaver())


def _message_for_action(action: str | None, message: str | None) -> str:
    if action == "accept_quote":
        return "Sí, confirmo"
    if action == "reject_quote":
        return "No, rechazo el presupuesto"
    return message or ""


def _as_decimal_text(value: Any) -> str:
    return f"{value:.2f}" if hasattr(value, "__format__") else str(value)


def _quote_for_result(pattern: str, result: dict[str, Any]) -> QuoteOut | None:
    status: str | None = None
    lines: list[QuoteLine] = []
    total: Any = None

    if pattern == "hierarchical":
        quote = result.get("quote")
        if result.get("outcome") == "awaiting_confirmation":
            status = "proposed"
        elif result.get("outcome") == "quoted":
            status = "saved"
        elif result.get("outcome") == "declined":
            status = "rejected"
        if quote and status:
            task_type = quote.get("labor_task_type", "maintenance")
            labor_name = (
                "Diagnóstico técnico"
                if task_type == "diagnosis"
                else "Mano de obra"
            )
            lines.append(
                QuoteLine(
                    label=labor_name,
                    amount=_as_decimal_text(quote["labor_cost"]),
                )
            )
            lines.extend(
                QuoteLine(
                    label=(
                        f"{part['name']} × {part['quantity']}"
                    ),
                    amount=_as_decimal_text(part["subtotal"]),
                )
                for part in quote.get("parts", [])
            )
            total = quote["total_amount"]

    elif pattern == "orchestrator":
        if result.get("awaiting_ticket_confirmation"):
            status = "proposed"
        elif result.get("ticket_cancelled"):
            status = "rejected"
        elif result.get("quote_id") is not None:
            status = "saved"
        if status:
            task_type = result.get("labor_task_type", "maintenance")
            labor_name = (
                "Diagnóstico técnico"
                if task_type == "diagnosis"
                else "Mano de obra"
            )
            lines.append(
                QuoteLine(
                    label=labor_name,
                    amount=_as_decimal_text(result.get("labor_cost", 0)),
                )
            )
            lines.extend(
                QuoteLine(
                    label=f"{part['name']} × {part['quantity']}",
                    amount=_as_decimal_text(
                        part["unit_price"] * int(part["quantity"])
                    ),
                )
                for part in result.get("available_parts", [])
            )
            total = result.get("total")

    if status is None or total is None:
        return None
    return QuoteOut(
        status=status,
        lines=lines,
        total=_as_decimal_text(total),
    )


def _reply_for_result(pattern: str, result: dict[str, Any]) -> str:
    if pattern == "orchestrator":
        reply = result.get("response")
        if isinstance(reply, str) and reply.strip():
            return reply
    messages = result.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage):
        content = messages[-1].content
        if isinstance(content, str) and content.strip():
            return content
    if messages and isinstance(messages[-1].content, str):
        return messages[-1].content
    raise ValueError("El patrón no produjo una respuesta de chat.")


def _ticket_for_result(pattern: str, result: dict[str, Any]) -> TicketOut | None:
    if pattern == "hierarchical" and result.get("outcome") == "quoted":
        code = result.get("ticket_code")
    elif pattern == "orchestrator" and result.get("quote_id") is not None:
        code = result.get("ticket_code")
    else:
        return None
    if not isinstance(code, str) or not code:
        return None
    return TicketOut(code=code, status="QUOTED")


def create_app(
    *,
    session_guard: SessionGuard | None = None,
    graph_factories: dict[str, GraphFactory] | None = None,
    settings_factory: Callable[[], Settings] = load_settings,
    trace_context_factory: Callable[[], AbstractContextManager[None]] | None = None,
) -> FastAPI:
    app = FastAPI(title="TechFix.AI · Patrones LangGraph", version="1.1.0")
    account_settings = (
        session_guard.settings
        if session_guard is not None
        else AccountSettings.from_env()
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(account_settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
    )
    app.add_exception_handler(SessionError, lambda _request, exc: JSONResponse(
        status_code=exc.status,
        content={"detail": exc.detail, "code": exc.code},
    ))
    app.add_exception_handler(
        RequestValidationError,
        lambda _request, exc: _validation_response(exc),
    )

    graph_builders = graph_factories or {
        "hierarchical": _build_hierarchical_graph,
        "orchestrator": _build_orchestrator_graph,
        "decentralized": _build_decentralized_graph,
    }
    if set(graph_builders) != set(PATTERN_NAMES):
        raise ValueError("Debe configurarse exactamente cada patrón disponible.")

    graph_cache: dict[str, Any] = {}
    conversations: dict[str, dict[str, Any]] = {}
    conversations_lock = RLock()
    limiter = LoginLimiter(20, 60)

    def get_guard() -> SessionGuard:
        nonlocal session_guard
        if session_guard is None:
            session_guard = SessionGuard.from_env()
        return session_guard

    def require_customer(request: Request) -> SessionCustomer:
        return get_guard().require_customer(request)

    def get_graph(pattern: str) -> Any:
        with conversations_lock:
            if pattern not in graph_cache:
                graph_cache[pattern] = graph_builders[pattern]()
            return graph_cache[pattern]

    def invoke_pattern(
        pattern: str,
        conversation_id: str,
        customer: SessionCustomer,
        message: str,
    ) -> dict[str, Any]:
        from app.agents.orquestador.graph.state import AgentState as OrchestratorState
        from app.agents.jerarquico.graph.state import ServiceState
        from app.agents.decentralized.state import AgentState as DecentralizedState

        human_message = HumanMessage(content=message)
        if pattern == "hierarchical":
            state: ServiceState = {
                "messages": [human_message],
                "customer_id": customer.id,
            }
        elif pattern == "orchestrator":
            state = OrchestratorState(
                messages=[human_message],
                user_id=customer.id,
            )
        else:
            state = DecentralizedState(messages=[human_message])

        config = {
            "configurable": {"thread_id": conversation_id},
            "run_name": f"techfix-{pattern}",
            "tags": ["service-chat", f"pattern:{pattern}"],
            "metadata": {
                "pattern": pattern,
                "conversation_id": conversation_id,
            },
        }
        with (trace_context_factory or (lambda: get_trace_context(settings_factory())))():
            return get_graph(pattern).invoke(state, config=config)

    @app.get("/api/chat/patterns")
    def patterns(_customer: SessionCustomer = Depends(require_customer)):
        return {
            "patterns": [
                {"id": pattern_id, "name": name}
                for pattern_id, name in PATTERN_NAMES.items()
            ]
        }

    @app.post("/api/chat", response_model=ChatOut, response_model_exclude_none=True)
    def chat(
        body: ChatIn,
        customer: SessionCustomer = Depends(require_customer),
    ) -> ChatOut:
        customer_key = str(customer.id)
        if limiter.blocked(customer_key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Enviaste muchos mensajes seguidos. Espera un minuto."},
            )
        limiter.fail(customer_key)

        is_new = body.conversation_id is None
        conversation_id = body.conversation_id or str(uuid4())
        with conversations_lock:
            conversation = conversations.get(conversation_id)
            if is_new:
                conversation = {
                    "customer_id": customer.id,
                    "pattern": body.pattern,
                    "pending_quote": False,
                    "lock": Lock(),
                }
                conversations[conversation_id] = conversation
            elif (
                conversation is None
                or conversation["customer_id"] != customer.id
            ):
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Conversación no encontrada.", "code": "not_found"},
                )
            elif conversation["pattern"] != body.pattern:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "Para cambiar de patrón, inicia una conversación nueva.",
                        "code": "pattern_locked",
                    },
                )

        assert conversation is not None
        if body.action and (
            body.pattern == "decentralized"
            or not conversation["pending_quote"]
        ):
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "No hay un presupuesto pendiente en esta conversación.",
                    "code": "no_quote",
                },
            )
        message = _message_for_action(body.action, body.message)

        with conversation["lock"]:
            try:
                result = invoke_pattern(
                    body.pattern,
                    conversation_id,
                    customer,
                    message,
                )
            except (SQLAlchemyError, OSError) as exc:
                logger.error(
                    "Pattern database or storage operation failed: %s",
                    type(exc).__name__,
                )
                raise HTTPException(
                    status_code=503,
                    detail="El asistente no pudo completar la operación.",
                ) from exc
            except GroqAPIError as exc:
                logger.error("Groq request failed: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=502,
                    detail="El proveedor LLM no pudo procesar el mensaje.",
                ) from exc
            except (OutputParserException, ValidationError, ValueError, LookupError, RuntimeError) as exc:
                logger.error("Pattern processing failed: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=502,
                    detail="El patrón no pudo completar el mensaje.",
                ) from exc

            quote = _quote_for_result(body.pattern, result)
            if body.pattern == "hierarchical":
                conversation["pending_quote"] = (
                    result.get("outcome") == "awaiting_confirmation"
                )
            elif body.pattern == "orchestrator":
                conversation["pending_quote"] = bool(
                    result.get("awaiting_ticket_confirmation")
                )
            answer = _reply_for_result(body.pattern, result)
            return ChatOut(
                conversation_id=conversation_id,
                reply=answer,
                quote=quote,
                ticket=_ticket_for_result(body.pattern, result),
                pattern=body.pattern,
            )

    return app


app = create_app()

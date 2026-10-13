"""Real FastAPI lifespan, mocked storage and graphs; no database or LLM."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.accounts.config import Settings
from app.accounts.session import SessionCustomer
import app.main as main


class Guard:
    settings = Settings(database_url=None, auth_secret="s" * 48, secure_cookie=False)

    def require_customer(self, request):
        return SimpleNamespace(id=1)


def resources():
    pool = MagicMock()
    pool.max_size = 5
    return SimpleNamespace(pool=pool, saver=MagicMock(), close=MagicMock())


@pytest.fixture(autouse=True)
def ownership_mock(monkeypatch):
    repository = MagicMock()
    repository.register.side_effect = lambda **kw: {"thread_id": kw["thread_id"]}
    monkeypatch.setattr(main, "ConversationOwnersRepository", lambda pool: repository)
    monkeypatch.setattr(main, "ConversationLocks", lambda pool: SimpleNamespace(hold=lambda thread: nullcontext()))


def test_lifespan_reuses_saver_and_closes(monkeypatch):
    storage = resources()
    graph = MagicMock()
    graph.get_state.return_value = SimpleNamespace(values={}, next=())
    graph.invoke.return_value = {"messages": [AIMessage(content="Respuesta")], "customer_id": 1}
    build = MagicMock(return_value=graph)
    monkeypatch.setattr(main, "_build_decentralized_graph", build)
    factory = MagicMock(return_value=storage)
    app = main.create_app(session_guard=Guard(), checkpoint_resources_factory=factory,
                          trace_context_factory=nullcontext)
    with TestClient(app) as client:
        for _ in range(2):
            assert client.post("/api/chat", json={"pattern": "decentralized", "message": "Hola"}).status_code == 200
        build.assert_called_once_with(storage.saver)
        factory.assert_called_once()
        storage.pool.open.assert_called_once_with(wait=True)
        storage.saver.setup.assert_not_called()
        storage.close.assert_not_called()
    storage.close.assert_called_once()
    assert app.state.decentralized_graph is None
    assert app.state.checkpoint_resources is None


@pytest.mark.parametrize("failure", ["factory", "open", "graph"])
def test_failure_no_fallback_other_pattern_survives(monkeypatch, failure):
    storage = resources()
    factory = MagicMock(return_value=storage)
    build = MagicMock(return_value=MagicMock())
    if failure == "factory":
        factory.side_effect = RuntimeError("private details")
    elif failure == "open":
        storage.pool.open.side_effect = RuntimeError("private details")
    else:
        build.side_effect = RuntimeError("private details")
    monkeypatch.setattr(main, "_build_decentralized_graph", build)
    other = MagicMock()
    other.invoke.return_value = {"messages": [AIMessage(content="Respuesta")], "outcome": "done"}
    monkeypatch.setattr(main, "_build_hierarchical_graph", lambda: other)
    app = main.create_app(session_guard=Guard(), checkpoint_resources_factory=factory,
                          trace_context_factory=nullcontext)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"pattern": "decentralized", "message": "Hola"})
        assert response.status_code == 503
        assert "private details" not in response.text
        assert client.post("/api/chat", json={"pattern": "hierarchical", "message": "Hola"}).status_code == 200
    assert storage.close.call_count == (0 if failure == "factory" else 1)


def test_runtime_database_failure_returns_503(monkeypatch):
    from psycopg import OperationalError
    storage = resources()
    graph = MagicMock()
    graph.get_state.return_value = SimpleNamespace(values={}, next=())
    graph.invoke.side_effect = OperationalError("private details")
    monkeypatch.setattr(main, "_build_decentralized_graph", lambda saver: graph)
    app = main.create_app(session_guard=Guard(), checkpoint_resources_factory=lambda: storage,
                          trace_context_factory=nullcontext)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"pattern": "decentralized", "message": "Hola"})
        assert response.status_code == 503 and "private details" not in response.text
    storage.close.assert_called_once()


def test_injected_graphs_do_not_open_storage():
    factory = MagicMock(side_effect=AssertionError("No storage"))
    app = main.create_app(session_guard=Guard(), graph_factories={name: MagicMock() for name in main.PATTERN_NAMES},
                          checkpoint_resources_factory=factory)
    with TestClient(app):
        factory.assert_not_called()

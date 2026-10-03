import pytest
from fastapi.testclient import TestClient
from app.agents.sales import DEMO_REQUEST
from app.auth import hash_password
from app.main import create_app


@pytest.fixture
def portal(tmp_path):
    users = {"ana": hash_password("prueba-ana-segura"), "luis": hash_password("prueba-luis-segura")}
    return create_app(users, tmp_path / "traces.jsonl", secure_cookie=False)


def client_for(app, username="ana"):
    client = TestClient(app, headers={"X-Portal-Request": "1"})
    result = client.post("/api/login", json={"username": username, "password": f"prueba-{username}-segura"})
    assert result.status_code == 200
    assert "HttpOnly" in result.headers["set-cookie"]
    return client


def test_authentication_and_logout(portal):
    guest = TestClient(portal)
    assert guest.get("/api/messages").status_code == 401
    assert guest.post("/api/chat", json={"message": "hola"}, headers={"X-Portal-Request": "1"}).status_code == 401
    assert guest.post("/api/login", json={"username": "ana", "password": "wrong"}).status_code == 403
    assert guest.post("/api/login", json={"username": "ana", "password": "wrong"}, headers={"X-Portal-Request": "1"}).status_code == 401
    client = client_for(portal)
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/messages").status_code == 401


def test_conversation_private_history_and_quotes(portal):
    ana, luis = client_for(portal), client_for(portal, "luis")
    reply = ana.post("/api/chat", json={"message": "Mi laptop no enciende"})
    assert reply.status_code == 200
    assert "cargador" in reply.json()["content"]
    assert reply.json()["execution_id"]
    assert len(ana.get("/api/messages").json()["messages"]) == 2
    assert luis.get("/api/messages").json()["messages"] == []
    assert "cargador" in ana.post("/api/chat", json={"message": "Es una Lenovo"}).json()["content"]
    assert ana.post("/api/chat", json={"message": "Quiero un presupuesto de ejemplo"}).json()["quote"]["total"] == "260.00"
    assert ana.post("/api/chat", json={"message": "Quiero cotizar"}).json()["quote"]["missing_data"]
    assert ana.post("/api/quotes", json=DEMO_REQUEST).json()["quote"]["total"] == "260.00"


def test_validation_and_static_portal(portal):
    client = client_for(portal)
    for message in ["", "  ", "x" * 4001]:
        assert client.post("/api/chat", json={"message": message}).status_code == 422
    page = client.get("/")
    assert page.status_code == 200
    assert 'id="messages"' in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/static/chat.js").status_code == 200


def test_generic_failure_does_not_leak(portal, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("SMTP_PASSWORD=super-secret")
    monkeypatch.setattr("app.main.invoke_traced", fail)
    client = client_for(portal)
    response = client.post("/api/chat", json={"message": "hola"})
    assert response.status_code == 503
    assert "super-secret" not in response.text
    assert client.get("/api/messages").json()["messages"] == []


def test_expired_session(portal, monkeypatch):
    client = client_for(portal)
    from time import monotonic
    future = monotonic() + 3601
    monkeypatch.setattr("app.main.monotonic", lambda: future)
    assert client.get("/api/messages").status_code == 401


def test_login_rate_limit(portal):
    client = TestClient(portal, headers={"X-Portal-Request": "1"})
    for _ in range(10):
        assert client.post("/api/login", json={"username": "ana", "password": "bad"}).status_code == 401
    assert client.post("/api/login", json={"username": "ana", "password": "bad"}).status_code == 429

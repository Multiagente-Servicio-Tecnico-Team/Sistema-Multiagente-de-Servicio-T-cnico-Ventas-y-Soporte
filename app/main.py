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

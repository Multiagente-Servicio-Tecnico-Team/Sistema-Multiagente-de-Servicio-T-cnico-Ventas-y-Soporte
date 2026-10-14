from __future__ import annotations

from functools import lru_cache
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator

from app.agents.orquestador import build_graph, new_thread_id
from app.database.repository import find_user_by_email


app = FastAPI(
    title="TechFix Multiagent API",
    version="1.0.0",
    description="API de atención y soporte multiagente con LangGraph, Groq y PostgreSQL.",
)
_sessions: dict[str, int] = {}


@lru_cache(maxsize=1)
def _agent_graph():
    return build_graph()


class IdentifyRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Ingresa un correo válido.")
        return value


class IdentifyResponse(BaseModel):
    user_id: int
    name: str
    thread_id: str
    greeting: str


class ChatRequest(BaseModel):
    user_id: int
    thread_id: str = Field(min_length=16, max_length=80)
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    ticket_id: int | None = None
    ticket_code: str | None = None
    quote_id: int | None = None
    payment_id: int | None = None
    payment_code: str | None = None
    warranty_code: str | None = None
    awaiting_input: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "techfix-api"}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_LOGIN_PAGE)


_LOGIN_PAGE = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>TechFix | Atención al cliente</title>
  <style>
    :root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#18322e;background:#f4f6f2}
    *{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px}
    main{width:min(100%,680px);background:#fff;border:1px solid #dce5df;border-radius:18px;overflow:hidden;box-shadow:0 18px 55px #173c3918}
    header{background:#153c39;color:white;padding:24px 28px}h1{margin:0;font-size:23px}header p{margin:7px 0 0;color:#d8e9df}
    section{padding:28px}.hidden{display:none!important}label{font-weight:600;display:block;margin-bottom:8px}
    input{width:100%;border:1px solid #b9c9c0;border-radius:9px;padding:12px;font-size:16px;color:#18322e}
    button{border:0;border-radius:9px;background:#153c39;color:white;padding:12px 18px;font-size:15px;font-weight:600;cursor:pointer}
    button:disabled{opacity:.55;cursor:wait}.row{display:flex;gap:10px;margin-top:12px}.row input{flex:1}
    #messages{height:360px;overflow:auto;background:#f7f9f7;border:1px solid #e2e9e4;border-radius:12px;padding:14px;margin-bottom:14px}
    .msg{white-space:pre-wrap;line-height:1.5;padding:10px 12px;border-radius:11px;margin:8px 0;max-width:90%}
    .assistant{background:#e9f1eb}.user{background:#d9e9e2;margin-left:auto}.error{color:#a12828;min-height:22px;margin-top:10px}
    footer{padding:0 28px 20px;color:#60756a;font-size:13px}a{color:#23675d}
  </style>
</head>
<body><main>
  <header><h1>TechFix · Atención al cliente</h1><p>Cuéntanos cómo podemos ayudarte.</p></header>
  <section id="login">
    <form id="login-form"><label for="email">Correo de un usuario activo</label>
      <input id="email" type="email" autocomplete="email" required placeholder="nombre@correo.com">
      <div class="row"><button id="login-button" type="submit">Continuar</button></div>
      <div id="login-error" class="error" role="alert"></div>
    </form>
  </section>
  <section id="chat-section" class="hidden">
    <div id="messages" aria-live="polite"></div>
    <form id="chat-form"><label for="message">Escribe tu consulta</label>
      <div class="row"><input id="message" maxlength="8000" required placeholder="Describe qué necesitas…"><button id="send-button" type="submit">Enviar</button></div>
    </form><div id="chat-error" class="error" role="alert"></div>
  </section>
  <footer>La documentación de la API está disponible en <a href="/docs">/docs</a>.</footer>
</main>
<script>
let session = null;
const $ = id => document.getElementById(id);
function addMessage(text, role){const node=document.createElement('div');node.className='msg '+role;node.textContent=text;$('messages').appendChild(node);$('messages').scrollTop=$('messages').scrollHeight;}
$('login-form').addEventListener('submit', async event=>{
  event.preventDefault(); $('login-button').disabled=true; $('login-error').textContent='';
  try {
    const response=await fetch('/api/v1/users/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:$('email').value})});
    const data=await response.json(); if(!response.ok) throw new Error(data.detail||'No se pudo iniciar sesión.');
    session=data; $('login').classList.add('hidden'); $('chat-section').classList.remove('hidden'); addMessage(data.greeting,'assistant'); $('message').focus();
  } catch(error){$('login-error').textContent=error.message||'No se pudo conectar con el servidor.';}
  finally{$('login-button').disabled=false;}
});
$('chat-form').addEventListener('submit',async event=>{
  event.preventDefault(); if(!session)return; const text=$('message').value.trim(); if(!text)return;
  $('message').value=''; addMessage(text,'user'); $('send-button').disabled=true; $('chat-error').textContent='';
  try {
    const response=await fetch('/api/v1/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:session.user_id,thread_id:session.thread_id,message:text})});
    const data=await response.json(); if(!response.ok) throw new Error(data.detail||'No se pudo completar la consulta.'); addMessage(data.response,'assistant');
  } catch(error){$('chat-error').textContent=error.message||'No se pudo conectar con el servidor.';}
  finally{$('send-button').disabled=false;$('message').focus();}
});
</script></body></html>"""


@app.post("/api/v1/users/identify", response_model=IdentifyResponse)
def identify_user(payload: IdentifyRequest):
    try:
        user = find_user_by_email(payload.email)
    except Exception as exc:
        # Avoid returning DB URLs, SQL parameters, or credentials to callers.
        raise HTTPException(status_code=503, detail=f"No se pudo consultar la base de datos ({type(exc).__name__}).") from exc
    if user is None:
        raise HTTPException(status_code=404, detail="No encontramos un usuario activo con ese correo.")
    name = str(user.get("name") or "Cliente")
    response = IdentifyResponse(
        user_id=int(user["id"]),
        name=name,
        thread_id=new_thread_id(),
        greeting=f"Hola, {name}. Cuéntame qué necesitas; te pediré confirmación antes de registrar una solicitud o cotización.",
    )
    _sessions[response.thread_id] = response.user_id
    return response


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    if _sessions.get(payload.thread_id) != payload.user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida. Identifica nuevamente tu correo.")
    try:
        graph = _agent_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content=payload.message)], "current_message": payload.message, "thread_id": payload.thread_id, "user_id": payload.user_id},
            {
                "configurable": {"thread_id": payload.thread_id},
                "run_name": "techfix-api-chat",
                "tags": ["fastapi", "orquestador"],
            },
        )
    except Exception as exc:
        # APIConnectionError is generally Groq networking; DB errors occur later in tool/nodes.
        detail = "No se pudo contactar al proveedor del modelo. Verifica conexión y configuración Groq."
        if type(exc).__name__ not in {"APIConnectionError", "ConnectError", "TimeoutException"}:
            detail = f"No se pudo completar la consulta ({type(exc).__name__}). Revisa los logs del servidor."
        raise HTTPException(status_code=502, detail=detail) from exc
    return ChatResponse(
        thread_id=payload.thread_id,
        response=str(result.get("response") or "No se recibió una respuesta del agente."),
        ticket_id=result.get("ticket_id"),
        ticket_code=result.get("ticket_code"),
        quote_id=result.get("quote_id"),
        payment_id=result.get("payment_id"),
        payment_code=result.get("payment_code"),
        warranty_code=result.get("warranty_code"),
        awaiting_input=bool(result.get("awaiting_input") or result.get("awaiting_clarification")),
    )


@app.post("/api/v1/sessions", response_model=IdentifyResponse)
def create_session(payload: IdentifyRequest):
    return identify_user(payload)

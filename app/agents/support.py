"""Orientación local y derivación comercial explícita, sin diagnóstico inventado."""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.sales import DEMO_REQUEST, build_sales_graph


class ChatState(TypedDict, total=False):
    message: str
    history: list[dict]
    route: str
    reply: str
    quote: dict


def router(state):
    text = state["message"].lower()
    return {"route": "sales" if any(word in text for word in ("presupuesto", "cotiza", "precio")) else "support"}


def support_agent(state):
    text = " ".join([m["content"] for m in state.get("history", []) if m["role"] == "user"] + [state["message"]]).lower()
    if any(word in text for word in ("humo", "quemado", "chispa", "hinchada")):
        reply = "Deja de usar el equipo y desconéctalo si puedes hacerlo sin riesgo. No lo abras ni vuelvas a cargarlo. Solicita revisión técnica presencial. ¿Qué equipo y modelo es?"
    elif any(word in text for word in ("no enciende", "no prende")):
        reply = "Comprueba la toma de corriente y la conexión del cargador compatible, sin abrir el equipo. ¿Se enciende algún indicador? Indica marca, modelo y desde cuándo ocurre."
    elif any(word in text for word in ("lento", "lentitud")):
        reply = "Reinicia el equipo, comprueba el espacio libre y anota cuándo aparece la lentitud. ¿Qué modelo y sistema operativo usas? No borres archivos sin copia de seguridad."
    else:
        reply = "Para orientarte, indica el tipo de equipo, marca, modelo, síntoma y cuándo empezó. Si aparece un error, describe su texto. No compartas contraseñas."
    return {"reply": reply + " Esta orientación inicial no confirma un diagnóstico."}


def build_chat_graph():
    sales = build_sales_graph()

    def sales_agent(state):
        demo = any(word in state["message"].lower() for word in ("demo", "ejemplo", "prueba"))
        quote = sales.invoke({"request": DEMO_REQUEST if demo else {}})["quote"]
        reply = ("Presupuesto de demostración: instalación S/ 80.00 + SSD S/ 180.00 = S/ 260.00. Son datos de prueba."
                 if demo else "Para cotizar necesito: " + "; ".join(quote["missing_data"]) + ". Un técnico debe confirmar los conceptos antes de asignar precios.")
        return {"reply": reply, "quote": quote}

    builder = StateGraph(ChatState)
    builder.add_node("router", router)
    builder.add_node("support_agent", support_agent)
    builder.add_node("sales_agent", sales_agent)
    builder.add_edge(START, "router")
    builder.add_conditional_edges("router", lambda state: state["route"], {"sales": "sales_agent", "support": "support_agent"})
    builder.add_edge("sales_agent", END)
    builder.add_edge("support_agent", END)
    return builder.compile(name="support_graph")

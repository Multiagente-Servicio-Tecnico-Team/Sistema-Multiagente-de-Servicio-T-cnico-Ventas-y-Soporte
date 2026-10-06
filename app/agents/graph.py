from __future__ import annotations

from decimal import Decimal
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.agents.quotes import calculate_quote
from app.agents.knowledge_base import retrieve_technical_knowledge
from app.config import CURRENCY, create_chat_model
from app.database.repository import (
    create_ticket,
    lookup_inventory,
    save_quote,
)


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: object
    ticket_id: int
    category: str
    product: str
    symptoms: str
    awaiting_clarification: bool
    clarification: str
    diagnosis: str
    labor_cost: Decimal
    requested_parts: list[dict[str, object]]
    inventory: list[dict[str, object]]
    quote_id: int
    total: Decimal
    response: str


class IntakeResult(BaseModel):
    category: str = Field(description="Tipo de solicitud en pocas palabras")
    product: str = Field(description="Equipo, marca y modelo si se mencionaron")
    symptoms: str = Field(description="Síntomas informados por el cliente")
    needs_clarification: bool = Field(
        description="True si falta información esencial para un diagnóstico inicial"
    )
    clarification_question: str = Field(
        description="Una pregunta concreta cuando hace falta aclarar; vacío en otro caso"
    )


class PartRequest(BaseModel):
    name: str = Field(description="Nombre específico del repuesto")
    quantity: int = Field(default=1, ge=1)


class TechnicalDiagnosis(BaseModel):
    diagnosis: str = Field(description="Diagnóstico técnico provisional y sus límites")
    labor_cost: Decimal = Field(ge=0, description="Costo estimado de mano de obra")
    parts: list[PartRequest] = Field(default_factory=list)


@tool
def consultar_inventario(nombre_repuesto: str, cantidad: int = 1) -> dict[str, object]:
    """Consulta existencias y precio actual de un repuesto en PostgreSQL."""
    item = lookup_inventory(nombre_repuesto, cantidad)
    item["unit_price"] = str(item["unit_price"])
    return item


TECHNICAL_SYSTEM_PROMPT = f"""
Eres el agente de soporte técnico de un taller. Emite un diagnóstico provisional,
no afirmes haber inspeccionado físicamente el equipo. Basa recomendaciones de
fallas y componentes en el contexto recuperado del catalogo tecnico Markdown.
Ese catalogo es orientativo, no confirma la causa ni compatibilidad. La moneda
para expresar la mano de obra es {CURRENCY}. No inventes compatibilidad, disponibilidad ni precios. Solicita aclaración si marca,
modelo o síntomas no permiten elegir repuestos con prudencia. Devuelve el costo de
mano de obra como estimación numérica en la moneda configurada por el negocio.
""".strip()


def _atencion_node(state: AgentState) -> dict[str, object]:
    model = create_chat_model().with_structured_output(IntakeResult)
    result = model.invoke(
        [
            (
                "system",
                "Eres atención al cliente. Extrae equipo, marca/modelo, síntomas e intención. "
                "Pregunta antes de derivar cuando falte información esencial. Responde en español.",
            ),
            *state.get("messages", []),
        ]
    )
    values: dict[str, object] = {
        "category": result.category,
        "product": result.product,
        "symptoms": result.symptoms,
        "awaiting_clarification": result.needs_clarification,
        "clarification": result.clarification_question,
    }

    if "ticket_id" not in state:
        values["ticket_id"] = create_ticket(state["user_id"], result.category)

    if result.needs_clarification:
        question = result.clarification_question or "¿Podrías compartir la marca, el modelo y cuándo ocurre la falla?"
        values["clarification"] = question
        values["response"] = question
        values["messages"] = [AIMessage(content=question)]
    return values


def _tecnico_node(state: AgentState) -> dict[str, object]:
    model = create_chat_model().with_structured_output(TechnicalDiagnosis)
    passages = retrieve_technical_knowledge(
        f"{state.get('product', '')} {state.get('symptoms', '')} {state.get('category', '')}"
    )
    knowledge_context = "\n\n".join(passages) or "No hubo coincidencias en el catalogo Markdown."
    result = model.invoke(
        [
            ("system", TECHNICAL_SYSTEM_PROMPT),
            (
                "human",
                f"Equipo: {state.get('product', 'No especificado')}\n"
                f"Síntomas: {state.get('symptoms', '')}\n"
                f"Categoría: {state.get('category', '')}\n\n"
                f"Contexto recuperado del catalogo tecnico local:\n{knowledge_context}",
            ),
        ]
    )
    return {
        "diagnosis": result.diagnosis,
        "labor_cost": result.labor_cost,
        "requested_parts": [part.model_dump() for part in result.parts],
    }


def _almacen_node(state: AgentState) -> dict[str, object]:
    inventory = [
        consultar_inventario.invoke(
            {"nombre_repuesto": part["name"], "cantidad": part["quantity"]}
        )
        for part in state.get("requested_parts", [])
    ]
    return {"inventory": inventory}


def _ventas_node(state: AgentState) -> dict[str, object]:
    inventory = state.get("inventory", [])
    available_parts = [part for part in inventory if part["available"]]
    unavailable_parts = [part for part in inventory if not part["available"]]
    labor_cost = Decimal(str(state.get("labor_cost", 0))).quantize(Decimal("0.01"))
    parts_total, total = calculate_quote(labor_cost, available_parts)
    quote_id, saved_total = save_quote(
        state["user_id"],
        state["ticket_id"],
        state["diagnosis"],
        labor_cost,
        available_parts,
    )
    if saved_total != total:
        raise RuntimeError("El total calculado no coincide con el presupuesto guardado")

    item_lines = [
        f"- {part['name']} x{part['quantity']}: "
        f"{CURRENCY} {Decimal(str(part['unit_price'])) * int(part['quantity']):,.2f}"
        for part in available_parts
    ]
    if unavailable_parts:
        item_lines.extend(
            f"- {part['requested_name']}: sin existencias suficientes "
            f"(solicitadas {part['quantity']}, disponibles {part['stock']})"
            for part in unavailable_parts
        )
    detail = "\n".join(item_lines) if item_lines else "- No se requieren repuestos"
    response = (
        f"Diagnóstico provisional: {state['diagnosis']}\n\n"
        f"Presupuesto #{quote_id} (pendiente de aceptación):\n"
        f"- Mano de obra: {CURRENCY} {labor_cost:,.2f}\n"
        f"{detail}\n"
        f"- Repuestos disponibles: {CURRENCY} {parts_total:,.2f}\n"
        f"- Total: {CURRENCY} {total:,.2f}\n\n"
        f"Ticket {state['ticket_id']} y evaluación guardados para tu usuario. "
        "La evaluación es estimada y debe confirmarse tras revisar físicamente el equipo."
    )
    return {
        "quote_id": quote_id,
        "total": total,
        "response": response,
        "messages": [AIMessage(content=response)],
    }


def build_graph():
    create_chat_model()
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", _supervisor_node)
    builder.add_node("atencion", _atencion_node)
    builder.add_node("tecnico", _tecnico_node)
    builder.add_node("almacen", _almacen_node)
    builder.add_node("ventas", _ventas_node)
    builder.add_edge(START, "atencion")
    builder.add_edge("atencion", "supervisor")
    builder.add_conditional_edges("supervisor", _supervisor_route)
    builder.add_edge("tecnico", "supervisor")
    builder.add_edge("almacen", "supervisor")
    builder.add_edge("ventas", "supervisor")
    return builder.compile(checkpointer=MemorySaver())


def _supervisor_node(state: AgentState) -> dict[str, object]:
    return {}


def _supervisor_route(state: AgentState) -> str:
    if state.get("awaiting_clarification"):
        return END
    if "diagnosis" not in state:
        return "tecnico"
    if "inventory" not in state:
        return "almacen"
    if "quote_id" not in state:
        return "ventas"
    return END


def new_thread_id() -> str:
    return str(uuid4())
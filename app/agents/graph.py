from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.schemas import IntakeDecision, TechnicalDiagnosis
from app.database.repository import ServiceRepository
from app.settings import Settings, load_settings


class ServiceState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    customer_email: str
    customer_id: int
    route: Literal["service", "clarification", "informational", "customer_not_found"]
    request_type: str
    title: str
    failure_description: str
    provisional_diagnosis: str
    estimated_labor_hours: Decimal
    required_parts: list[dict[str, Any]]
    matched_parts: list[dict[str, Any]]
    ticket_id: int
    ticket_code: str
    quote_id: int
    quote: dict[str, Any]
    outcome: str


def calculate_quote(
    *,
    labor_hours: Decimal,
    labor_hourly_rate: Decimal,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    money = Decimal("0.01")
    labor_cost = (labor_hours * labor_hourly_rate).quantize(
        money,
        rounding=ROUND_HALF_UP,
    )
    quote_parts = []
    for part in parts:
        quantity = int(part["quantity"])
        unit_price = Decimal(str(part["unit_price"]))
        subtotal = (unit_price * quantity).quantize(money, rounding=ROUND_HALF_UP)
        quote_parts.append(
            {
                **part,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    parts_cost = sum(
        (part["subtotal"] for part in quote_parts),
        start=Decimal("0.00"),
    )
    total_amount = labor_cost + parts_cost
    maximum_amount = Decimal("99999999.99")
    if total_amount > maximum_amount:
        raise ValueError(
            "El importe calculado excede el límite del esquema de cotizaciones."
        )
    return {
        "labor_hours": labor_hours,
        "labor_hourly_rate": labor_hourly_rate,
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total_amount": total_amount,
        "parts": quote_parts,
    }


def _after_intake(state: ServiceState) -> str:
    if state.get("route") == "service":
        return "technical_support"
    return END


def _after_inventory(state: ServiceState) -> str:
    if state.get("outcome") == "inventory_confirmed":
        return "sales"
    return "unavailable_response"


def build_multiagent_graph(
    *,
    settings: Settings | None = None,
    repository: ServiceRepository | None = None,
    model: Any | None = None,
):
    settings = settings or load_settings()
    settings.require_chat_configuration()
    repository = repository or ServiceRepository()
    llm = model or ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )

    def customer_care_supervisor(state: ServiceState) -> dict[str, Any]:
        customer = repository.find_customer(state["customer_email"])
        if not customer:
            return {
                "route": "customer_not_found",
                "messages": [
                    AIMessage(
                        content=(
                            "No encontré un cliente activo registrado con ese email. "
                            "Verifica que ingresaste el correo de un usuario CUSTOMER "
                            "existente y vuelve a intentarlo."
                        )
                    )
                ],
            }

        decision = llm.with_structured_output(IntakeDecision).invoke(
            [
                SystemMessage(
                    content=(
                        "Eres el supervisor de atención de un servicio técnico. "
                        "Clasifica la conversación como service solo cuando describa "
                        "una falla o solicitud de soporte técnico que requiera "
                        "diagnóstico. Usa clarification si faltan equipo o síntomas "
                        "esenciales y escribe una pregunta concreta. Usa "
                        "informational para consultas fuera de ese flujo. No inventes "
                        "datos, diagnósticos, precios ni disponibilidad."
                    )
                ),
                *state["messages"],
            ]
        )
        if decision.route == "clarification":
            question = (decision.clarification_question or "").strip()
            if not question:
                raise ValueError(
                    "El supervisor clasificó una aclaración sin proporcionar "
                    "la pregunta."
                )
            return {
                "route": "clarification",
                "messages": [AIMessage(content=question)],
            }
        if decision.route == "informational":
            response = (decision.informational_response or "").strip()
            if not response:
                response = (
                    "Puedo ayudarte a registrar y cotizar solicitudes de reparación "
                    "o soporte técnico. Cuéntame qué falla presenta tu equipo."
                )
            return {
                "route": "informational",
                "messages": [AIMessage(content=response)],
            }

        required_values = (
            decision.request_type,
            decision.title,
            decision.failure_description,
        )
        if not all(value and value.strip() for value in required_values):
            raise ValueError(
                "El supervisor clasificó un servicio sin los datos requeridos."
            )
        return {
            "route": "service",
            "customer_id": int(customer["id"]),
            "request_type": decision.request_type,
            "title": decision.title.strip(),
            "failure_description": decision.failure_description.strip(),
        }

    def technical_support_agent(state: ServiceState) -> dict[str, Any]:
        diagnosis = llm.with_structured_output(TechnicalDiagnosis).invoke(
            [
                SystemMessage(
                    content=(
                        "Eres el agente de soporte técnico. Con base solo en la "
                        "descripción del cliente, formula un diagnóstico provisional, "
                        "estima las horas de mano de obra y enumera los repuestos "
                        "necesarios por nombre exacto o código cuando sea posible. "
                        "No inventes stock ni precios. Si no se requiere repuesto, "
                        "devuelve una lista vacía."
                    )
                ),
                *state["messages"],
            ]
        )
        return {
            "provisional_diagnosis": diagnosis.provisional_diagnosis.strip(),
            "estimated_labor_hours": diagnosis.estimated_labor_hours,
            "required_parts": [
                part.model_dump() for part in diagnosis.required_parts
            ],
        }

    def create_analysis_ticket(state: ServiceState) -> dict[str, Any]:
        settings.require_labor_hourly_rate()
        ticket_code = "ST-" + uuid4().hex[:12].upper()
        ticket_id = repository.create_ticket(
            code=ticket_code,
            customer_id=state["customer_id"],
            title=state["title"][:200],
            failure_description=state["failure_description"],
            request_type=state["request_type"],
            provisional_diagnosis=state["provisional_diagnosis"],
        )
        return {"ticket_id": ticket_id, "ticket_code": ticket_code}

    def warehouse_agent(state: ServiceState) -> dict[str, Any]:
        confirmed_parts = []
        for requested in state["required_parts"]:
            candidates = repository.find_spare_parts(requested["search_term"])
            if len(candidates) != 1:
                names = ", ".join(part["name"] for part in candidates)
                detail = (
                    f"Encontré varias coincidencias para "
                    f"'{requested['search_term']}': {names}. "
                    if candidates
                    else f"No encontré el repuesto '{requested['search_term']}'. "
                )
                return {
                    "outcome": "inventory_unavailable",
                    "messages": [
                        AIMessage(
                            content=(
                                f"El ticket {state['ticket_code']} quedó abierto en "
                                f"análisis. {detail}No guardaré una cotización hasta "
                                "confirmar el repuesto correcto y su disponibilidad."
                            )
                        )
                    ],
                }

            part = candidates[0]
            if int(part["current_stock"]) < int(requested["quantity"]):
                return {
                    "outcome": "inventory_unavailable",
                    "messages": [
                        AIMessage(
                            content=(
                                f"El ticket {state['ticket_code']} quedó abierto en "
                                f"análisis, pero no hay stock suficiente de "
                                f"{part['name']} para la cantidad solicitada. "
                                "No guardaré una cotización parcial."
                            )
                        )
                    ],
                }
            confirmed_parts.append(
                {
                    "id": int(part["id"]),
                    "code": part["code"],
                    "name": part["name"],
                    "quantity": int(requested["quantity"]),
                    "unit_price": Decimal(str(part["unit_price"])),
                }
            )
        return {
            "outcome": "inventory_confirmed",
            "matched_parts": confirmed_parts,
        }

    def sales_agent(state: ServiceState) -> dict[str, Any]:
        rate = settings.require_labor_hourly_rate()
        quote = calculate_quote(
            labor_hours=state["estimated_labor_hours"],
            labor_hourly_rate=rate,
            parts=state["matched_parts"],
        )
        return {"quote": quote}

    def persist_quote(state: ServiceState) -> dict[str, Any]:
        quote = state["quote"]
        quote_id = repository.save_quote(
            ticket_id=state["ticket_id"],
            labor_cost=quote["labor_cost"],
            parts_cost=quote["parts_cost"],
            total_amount=quote["total_amount"],
            observations=(
                f"Diagnóstico provisional: {state['provisional_diagnosis']}"
            ),
            parts=quote["parts"],
        )
        return {"quote_id": quote_id}

    def customer_care_response(state: ServiceState) -> dict[str, Any]:
        quote = state["quote"]
        lines = [
            f"El ticket {state['ticket_code']} y su cotización quedaron registrados.",
            f"Diagnóstico provisional: {state['provisional_diagnosis']}",
            (
                f"Mano de obra ({quote['labor_hours']} h): "
                f"{quote['labor_cost']:.2f}"
            ),
        ]
        lines.extend(
            f"{part['name']} x {part['quantity']} "
            f"({part['unit_price']:.2f} c/u): {part['subtotal']:.2f}"
            for part in quote["parts"]
        )
        lines.extend(
            [
                f"Repuestos: {quote['parts_cost']:.2f}",
                f"Total: {quote['total_amount']:.2f}",
                "La cotización queda pendiente de aceptación.",
            ]
        )
        return {
            "outcome": "quoted",
            "messages": [AIMessage(content="\n".join(lines))],
        }

    graph = StateGraph(ServiceState)
    graph.add_node("customer_care_supervisor", customer_care_supervisor)
    graph.add_node("technical_support_agent", technical_support_agent)
    graph.add_node("create_analysis_ticket", create_analysis_ticket)
    graph.add_node("warehouse_agent", warehouse_agent)
    graph.add_node("sales_agent", sales_agent)
    graph.add_node("persist_quote", persist_quote)
    graph.add_node("customer_care_response", customer_care_response)

    graph.add_edge(START, "customer_care_supervisor")
    graph.add_conditional_edges(
        "customer_care_supervisor",
        _after_intake,
        {
            "technical_support": "technical_support_agent",
            END: END,
        },
    )
    graph.add_edge("technical_support_agent", "create_analysis_ticket")
    graph.add_edge("create_analysis_ticket", "warehouse_agent")
    graph.add_conditional_edges(
        "warehouse_agent",
        _after_inventory,
        {
            "sales": "sales_agent",
            "unavailable_response": END,
        },
    )
    graph.add_edge("sales_agent", "persist_quote")
    graph.add_edge("persist_quote", "customer_care_response")
    graph.add_edge("customer_care_response", END)

    return graph.compile(checkpointer=InMemorySaver())

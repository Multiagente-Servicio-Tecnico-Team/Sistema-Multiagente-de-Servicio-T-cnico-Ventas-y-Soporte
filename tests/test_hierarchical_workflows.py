from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.agents.jerarquico.agents.logistics import LogisticsDecision
from app.agents.jerarquico.agents.warranty import make_warranty_agent
from app.agents.jerarquico.graph.builder import build_multiagent_graph
from app.agents.jerarquico.schemas import (
    IntakeDecision,
    PartRequest,
    QuoteConfirmation,
)
from app.settings import Settings


class FakeSaleModel:
    def __init__(self, route="sale"):
        self.route = route

    def with_structured_output(self, schema):
        model = self

        class Result:
            def invoke(self, _messages):
                if schema is IntakeDecision:
                    return IntakeDecision(
                        route=model.route,
                        request_type="SALE" if model.route == "sale" else "PC_BUILD",
                        title="Compra de prueba",
                        failure_description="Solicitud comercial de prueba",
                        required_parts=[
                            PartRequest(search_term="Mouse Gamer", quantity=2)
                        ],
                    )
                if schema is QuoteConfirmation:
                    return QuoteConfirmation(decision="confirm")
                if schema is LogisticsDecision:
                    return LogisticsDecision(mode="PHYSICAL_STORE")
                raise AssertionError(f"Unexpected schema: {schema}")

        return Result()

    def invoke(self, _messages):
        return SimpleNamespace(content="Respuesta FAQ de prueba.")


class FakeCommercialRepository:
    def __init__(self):
        self.created_ticket = None
        self.saved_order = None
        self.logistics = None

    def find_customer(self, _email):
        return {"id": 12}

    def create_intake_ticket(self, **values):
        self.created_ticket = values
        return 41

    def find_spare_parts(self, _search_term):
        return [
            {
                "id": 7,
                "code": "MOU-001",
                "name": "Mouse Gamer Logitech",
                "unit_price": Decimal("24.50"),
                "current_stock": 5,
            }
        ]

    def accept_ticket_quote(self, **values):
        self.saved_order = values
        return {
            "quote_id": 51,
            "payment_id": 61,
            "payment_code": "PAY-TEST",
            "payment_status": "PENDING",
        }

    def cancel_ticket(self, _ticket_id, _customer_id):
        raise AssertionError("The test accepts the proposal.")

    def create_logistics_record(self, **values):
        self.logistics = values
        return 71


def make_settings():
    return Settings(
        groq_api_key="test-key",
        groq_model="test-model",
        database_url="postgresql://unused",
        langsmith_api_key=None,
        langsmith_tracing=False,
        langsmith_project="tests",
        langsmith_hide_inputs=True,
        langsmith_hide_outputs=True,
        labor_maintenance_price=Decimal("40.00"),
        labor_diagnosis_price=Decimal("50.00"),
        labor_pc_build_price=Decimal("50.00"),
    )


def test_direct_sale_queries_catalog_and_creates_payment_only_after_acceptance():
    repository = FakeCommercialRepository()
    graph = build_multiagent_graph(
        settings=make_settings(),
        repository=repository,
        model=FakeSaleModel(),
    )
    config = {"configurable": {"thread_id": "sale-flow"}}

    proposal = graph.invoke(
        {
            "messages": [
                HumanMessage(content="Quiero comprar dos mouse gamer.")
            ],
            "customer_id": 12,
        },
        config=config,
    )

    assert proposal["outcome"] == "awaiting_confirmation"
    assert proposal["quote_type"] == "DIRECT_SALE"
    assert proposal["quote"]["labor_cost"] == Decimal("0.00")
    assert proposal["quote"]["total_amount"] == Decimal("49.00")
    assert repository.created_ticket["request_type"] == "SALE"
    assert repository.saved_order is None

    accepted = graph.invoke(
        {"messages": [HumanMessage(content="Sí, acepto")]},
        config=config,
    )

    assert accepted["outcome"] == "quoted"
    assert accepted["ticket_status"] == "PAYMENT_PENDING"
    assert accepted["payment_code"] == "PAY-TEST"
    assert repository.saved_order["quote_type"] == "DIRECT_SALE"
    assert repository.saved_order["parts"][0]["subtotal"] == Decimal("49.00")
    assert "PENDIENTE" in accepted["messages"][-1].content

    logistics = graph.invoke(
        {"messages": [HumanMessage(content="Lo recojo en tienda")]},
        config=config,
    )

    assert logistics["outcome"] == "logistics_registered"
    assert repository.logistics["mode"] == "PHYSICAL_STORE"


def test_pc_build_stops_when_catalog_cannot_verify_component_compatibility():
    graph = build_multiagent_graph(
        settings=make_settings(),
        repository=FakeCommercialRepository(),
        model=FakeSaleModel(route="pc_build"),
    )

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="Quiero armar una PC.")],
            "customer_id": 12,
        },
        config={"configurable": {"thread_id": "pc-build-flow"}},
    )

    assert result["outcome"] == "inventory_unavailable"
    assert result.get("quote") is None
    assert "compatibilidad" in result["messages"][-1].content


def test_warranty_status_lookup_is_scoped_to_authenticated_customer():
    class WarrantyRepository:
        def find_warranty(self, _code):
            return {
                "id": 9,
                "customer_id": 12,
                "warranty_code": "WAR-TEST",
                "item_or_service_name": "Pantalla",
                "warranty_months": 3,
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 4, 1),
                "status": "ACTIVE",
                "not_expired": True,
            }

    agent = make_warranty_agent(WarrantyRepository())
    result = agent(
        {
            "messages": [HumanMessage(content="¿Sigue vigente?")],
            "request_type": "WARRANTY_STATUS_CHECK",
            "warranty_code": "WAR-TEST",
            "customer_id": 12,
        }
    )

    assert result["outcome"] == "warranty_status_checked"
    assert "vigente" in result["messages"][-1].content

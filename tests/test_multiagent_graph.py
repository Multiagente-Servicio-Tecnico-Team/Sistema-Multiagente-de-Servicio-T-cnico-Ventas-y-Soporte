import unittest
from dataclasses import replace
from decimal import Decimal

from app.agents.graph import build_multiagent_graph, calculate_quote
from app.agents.schemas import IntakeDecision, PartRequest, TechnicalDiagnosis
from app.settings import Settings


class FakeStructuredModel:
    def __init__(
        self,
        intake: IntakeDecision,
        diagnosis: TechnicalDiagnosis,
    ) -> None:
        self.intake = intake
        self.diagnosis = diagnosis

    def with_structured_output(self, schema):
        return FakeStructuredResponse(self, schema)


class FakeStructuredResponse:
    def __init__(self, model: FakeStructuredModel, schema) -> None:
        self.model = model
        self.schema = schema

    def invoke(self, messages):
        del messages
        if self.schema is IntakeDecision:
            return self.model.intake
        if self.schema is TechnicalDiagnosis:
            return self.model.diagnosis
        raise AssertionError(f"Unexpected structured schema: {self.schema}")


class FakeRepository:
    def __init__(self, *, customer=True, stock=10) -> None:
        self.customer = (
            {"id": 12, "name": "Ana", "last_name": "Prueba"} if customer else None
        )
        self.stock = stock
        self.created_ticket = None
        self.saved_quote = None

    def find_customer(self, email):
        del email
        return self.customer

    def create_ticket(self, **values):
        self.created_ticket = values
        return 84

    def find_spare_parts(self, search_term):
        del search_term
        return [
            {
                "id": 7,
                "code": "FAN-01",
                "name": "Ventilador interno",
                "unit_price": Decimal("10.25"),
                "current_stock": self.stock,
            }
        ]

    def save_quote(self, **values):
        self.saved_quote = values
        return 91


def make_settings() -> Settings:
    return Settings(
        groq_api_key="test-key",
        groq_model="test-model",
        database_url="postgresql+pg8000://user:password@localhost/test",
        langsmith_api_key=None,
        langsmith_tracing=False,
        langsmith_project="test-project",
        labor_hourly_rate=Decimal("80.00"),
    )


def make_model(
    intake: IntakeDecision | None = None,
    diagnosis: TechnicalDiagnosis | None = None,
) -> FakeStructuredModel:
    return FakeStructuredModel(
        intake=intake
        or IntakeDecision(
            route="service",
            request_type="REPAIR",
            title="Laptop se apaga",
            failure_description="Se calienta y se apaga.",
        ),
        diagnosis=diagnosis
        or TechnicalDiagnosis(
            provisional_diagnosis="Posible falla de ventilación.",
            estimated_labor_hours=Decimal("1.50"),
            required_parts=[PartRequest(search_term="Ventilador interno", quantity=2)],
        ),
    )


def invoke(graph):
    return graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Mi laptop se calienta y se apaga.",
                }
            ],
            "customer_email": "ana@example.com",
            "outcome": "pending",
            "ticket_id": None,
            "ticket_code": "",
            "quote_id": None,
            "quote": None,
        },
        config={
            "configurable": {"thread_id": "test-session"},
            "metadata": {"session_id": "test-session"},
        },
    )


class MultiagentGraphTests(unittest.TestCase):
    def test_calculates_totals_without_floating_point_arithmetic(self):
        quote = calculate_quote(
            labor_hours=Decimal("1.50"),
            labor_hourly_rate=Decimal("80.00"),
            parts=[
                {
                    "id": 7,
                    "name": "Ventilador",
                    "quantity": 2,
                    "unit_price": Decimal("10.25"),
                }
            ],
        )

        self.assertEqual(quote["labor_cost"], Decimal("120.00"))
        self.assertEqual(quote["parts_cost"], Decimal("20.50"))
        self.assertEqual(quote["total_amount"], Decimal("140.50"))
        self.assertEqual(quote["parts"][0]["subtotal"], Decimal("20.50"))

    def test_runs_hierarchical_flow_and_persists_quote(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "quoted")
        self.assertEqual(repository.created_ticket["customer_id"], 12)
        self.assertEqual(repository.created_ticket["request_type"], "REPAIR")
        self.assertEqual(repository.saved_quote["ticket_id"], 84)
        self.assertEqual(repository.saved_quote["total_amount"], Decimal("140.50"))
        self.assertIn("ST-", result["messages"][-1].content)
        self.assertIn("140.50", result["messages"][-1].content)

    def test_stock_shortage_leaves_ticket_in_analysis_without_quote(self):
        repository = FakeRepository(stock=1)
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertIsNotNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("no hay stock suficiente", result["messages"][-1].content)

    def test_requires_customer_record_before_creating_ticket(self):
        repository = FakeRepository(customer=False)
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["route"], "customer_not_found")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)

    def test_clarification_does_not_create_ticket(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="clarification",
                    clarification_question="¿Qué modelo de laptop tienes?",
                )
            ),
        )

        result = invoke(graph)

        self.assertEqual(result["route"], "clarification")
        self.assertIsNone(repository.created_ticket)
        self.assertIn("¿Qué modelo", result["messages"][-1].content)

    def test_missing_labor_rate_does_not_create_ticket(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=replace(make_settings(), labor_hourly_rate=None),
            repository=repository,
            model=make_model(),
        )

        with self.assertRaisesRegex(RuntimeError, "LABOR_HOURLY_RATE"):
            invoke(graph)
        self.assertIsNone(repository.created_ticket)


if __name__ == "__main__":
    unittest.main()

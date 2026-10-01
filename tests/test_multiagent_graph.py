import unittest
from dataclasses import replace
from decimal import Decimal

from app.agents.graph import build_multiagent_graph, calculate_quote
from app.agents.schemas import (
    IntakeDecision,
    PartRequest,
    QuoteConfirmation,
    TechnicalDiagnosis,
)
from app.settings import Settings


class FakeStructuredModel:
    def __init__(
        self,
        intake: IntakeDecision,
        diagnosis: TechnicalDiagnosis,
        confirmation: QuoteConfirmation,
    ) -> None:
        self.intake = intake
        self.diagnosis = diagnosis
        self.confirmation = confirmation

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
        if self.schema is QuoteConfirmation:
            return self.model.confirmation
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

    def create_ticket_with_quote(self, **values):
        self.created_ticket = values
        self.saved_quote = values
        return 84, 91

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


class AdjustableRateSettings:
    def __init__(self) -> None:
        self.labor_hourly_rate = Decimal("80.00")

    def require_chat_configuration(self) -> None:
        return None

    def require_labor_hourly_rate(self) -> Decimal:
        return self.labor_hourly_rate


def make_settings() -> Settings:
    return Settings(
        groq_api_key="test-key",
        groq_model="test-model",
        database_url="postgresql+pg8000://user:password@localhost/test",
        langsmith_api_key=None,
        langsmith_tracing=False,
        langsmith_project="test-project",
        langsmith_hide_inputs=True,
        langsmith_hide_outputs=True,
        labor_hourly_rate=Decimal("80.00"),
    )


def make_model(
    intake: IntakeDecision | None = None,
    diagnosis: TechnicalDiagnosis | None = None,
    confirmation: QuoteConfirmation | None = None,
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
        confirmation=confirmation
        or QuoteConfirmation(decision="confirm"),
    )


def invoke(graph, message="Mi laptop se calienta y se apaga.", *, initial=True):
    values = {
        "messages": [{"role": "user", "content": message}],
    }
    if initial:
        values.update(
            {
                "customer_email": "ana@example.com",
                "outcome": "pending",
                "awaiting_quote_confirmation": False,
                "ticket_id": None,
                "ticket_code": "",
                "quote_id": None,
                "quote": None,
            }
        )
    return graph.invoke(
        values,
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

    def test_suggests_rag_diagnosis_without_persisting_before_confirmation(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertTrue(result["awaiting_quote_confirmation"])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertEqual(
            [document["id"] for document in result["rag_documents"]],
            ["CASE-LAPTOP-OVERHEAT-01"],
        )
        self.assertIn("Total indicativo calculado: 140.50", result["messages"][-1].content)

    def test_confirmation_persists_ticket_and_quote_atomically(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        suggestion = invoke(graph)
        self.assertIsNone(repository.created_ticket)
        self.assertEqual(suggestion["outcome"], "awaiting_confirmation")

        result = invoke(graph, "Sí, confirma", initial=False)

        self.assertEqual(result["outcome"], "quoted")
        self.assertFalse(result["awaiting_quote_confirmation"])
        self.assertEqual(repository.created_ticket["customer_id"], 12)
        self.assertEqual(repository.created_ticket["request_type"], "REPAIR")
        self.assertEqual(repository.saved_quote["total_amount"], Decimal("140.50"))
        self.assertIn("ST-", result["messages"][-1].content)
        self.assertIn("140.50", result["messages"][-1].content)

    def test_stock_change_requires_a_new_confirmation(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        invoke(graph)
        repository.stock = 9
        result = invoke(graph, "Sí, confirma", initial=False)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertTrue(result["awaiting_quote_confirmation"])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("propuesta anterior", result["messages"][-1].content)
        self.assertIn("valores actualizados", result["messages"][-1].content)

    def test_labor_rate_change_requires_a_new_confirmation(self):
        repository = FakeRepository()
        settings = AdjustableRateSettings()
        graph = build_multiagent_graph(
            settings=settings,
            repository=repository,
            model=make_model(),
        )

        invoke(graph)
        settings.labor_hourly_rate = Decimal("90.00")
        result = invoke(graph, "Sí, confirma", initial=False)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("tarifa de mano de obra", result["messages"][-1].content)
        self.assertIn("Total indicativo calculado: 155.50", result["messages"][-1].content)

    def test_declining_suggestion_does_not_persist_data(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                confirmation=QuoteConfirmation(decision="decline"),
            ),
        )

        invoke(graph)
        result = invoke(graph, "No, gracias", initial=False)

        self.assertEqual(result["outcome"], "declined")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("No guardé", result["messages"][-1].content)

    def test_unclear_confirmation_keeps_pending_suggestion(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                confirmation=QuoteConfirmation(decision="unclear"),
            ),
        )

        invoke(graph)
        result = invoke(graph, "¿Puedo pensarlo?", initial=False)

        self.assertEqual(result["route"], "awaiting_confirmation")
        self.assertTrue(result["awaiting_quote_confirmation"])
        self.assertIsNone(repository.created_ticket)
        self.assertIn("¿Confirmas", result["messages"][-1].content)

    def test_stock_shortage_does_not_persist_ticket_or_quote(self):
        repository = FakeRepository(stock=1)
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("stock actual es insuficiente", result["messages"][-1].content)

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

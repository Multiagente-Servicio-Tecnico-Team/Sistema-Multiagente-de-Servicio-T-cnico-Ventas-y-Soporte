import unittest
from dataclasses import replace
from decimal import Decimal

from app.agents.graph import build_multiagent_graph, calculate_quote
from app.agents.retriever import MarkdownKnowledgeRetriever
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
    def __init__(self, *, customer=True, stock=10, unit_price=Decimal("10.25")) -> None:
        self.customer = (
            {"id": 12, "name": "Ana", "last_name": "Prueba"} if customer else None
        )
        self.stock = stock
        self.unit_price = unit_price
        self.lookups = []
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
        self.lookups.append(search_term)
        part_id = 7 if search_term == "Pasta_Termica" else 8
        return [
            {
                "id": part_id,
                "code": search_term,
                "name": search_term.replace("_", " "),
                "unit_price": self.unit_price,
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
            title="Laptop se calienta",
            failure_description="El ventilador suena fuerte y la temperatura es alta.",
        ),
        diagnosis=diagnosis
        or TechnicalDiagnosis(
            provisional_diagnosis="Posible falla de ventilación.",
            estimated_labor_hours=Decimal("1.50"),
            required_parts=[
                PartRequest(search_term="Pasta_Termica", quantity=1),
                PartRequest(search_term="Ventilador_CPU", quantity=1),
            ],
        ),
        confirmation=confirmation
        or QuoteConfirmation(decision="confirm"),
    )


def invoke(
    graph,
    message="Mi laptop se calienta y el ventilador suena fuerte.",
    *,
    initial=True,
):
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
    def test_intake_schema_accepts_provider_response_above_previous_limit(self):
        long_response = "Recomendación paso a paso. " * 100
        decision = IntakeDecision(
            route="service",
            request_type="REPAIR",
            title="Laptop lenta",
            failure_description="Demora en arrancar",
            informational_response=long_response,
        )

        self.assertEqual(decision.informational_response, long_response)
        schema = IntakeDecision.model_json_schema()
        self.assertEqual(
            schema["properties"]["informational_response"]["anyOf"][0]["maxLength"],
            4000,
        )

    def test_diagnosis_normalizes_labor_hour_range_to_midpoint(self):
        diagnosis = TechnicalDiagnosis(
            provisional_diagnosis="Posible unidad lenta.",
            estimated_labor_hours="1-2",
        )

        self.assertEqual(diagnosis.estimated_labor_hours, Decimal("1.5"))

    def test_diagnosis_normalizes_decimal_comma_range(self):
        diagnosis = TechnicalDiagnosis(
            provisional_diagnosis="Posible unidad lenta.",
            estimated_labor_hours="1,0–2,0",
        )

        self.assertEqual(diagnosis.estimated_labor_hours, Decimal("1.5"))

    def test_diagnosis_rejects_invalid_labor_hour_ranges(self):
        for value in ("2-1", "0-101"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TechnicalDiagnosis(
                    provisional_diagnosis="Diagnóstico provisional.",
                    estimated_labor_hours=value,
                )

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

    def test_quote_rejects_missing_or_zero_price_parts(self):
        with self.assertRaisesRegex(ValueError, "sin artículos"):
            calculate_quote(
                labor_hours=Decimal("1.00"),
                labor_hourly_rate=Decimal("80.00"),
                parts=[],
            )

        with self.assertRaisesRegex(ValueError, "precio positivos"):
            calculate_quote(
                labor_hours=Decimal("1.00"),
                labor_hourly_rate=Decimal("80.00"),
                parts=[
                    {
                        "id": 7,
                        "quantity": 1,
                        "unit_price": Decimal("0"),
                    }
                ],
            )

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
            ["manual_servicio:007"],
        )
        self.assertEqual(
            repository.lookups,
            ["Pasta_Termica", "Ventilador_CPU"],
        )
        self.assertIn("Total indicativo calculado: 140.50", result["messages"][-1].content)
        self.assertIn("Orientación técnica preliminar", result["messages"][-1].content)

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
        repository = FakeRepository(stock=0)
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

    def test_zero_catalog_price_does_not_produce_or_persist_a_quote(self):
        repository = FakeRepository(unit_price=Decimal("0.00"))
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("precio positivo", result["messages"][-1].content)

    def test_no_identified_parts_cannot_generate_a_zero_material_quote(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Requiere revisión técnica.",
                    estimated_labor_hours=Decimal("1.00"),
                    required_parts=[],
                )
            ),
            retriever=MarkdownKnowledgeRetriever(documents=()),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertEqual(repository.lookups, [])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("materiales en cero", result["messages"][-1].content)

    def test_unresolved_manual_alternatives_do_not_create_a_quote(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="PC se apaga poco después de encender",
                    failure_description="Se apaga dos segundos después de encender.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Posible fallo de alimentación.",
                    estimated_labor_hours=Decimal("1.00"),
                    required_parts=[],
                ),
            ),
        )

        result = invoke(graph, "La PC se apaga al encender.")

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertEqual(repository.lookups, [])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("alternativas", result["messages"][-1].content)

    def test_selected_manual_alternative_is_the_only_catalog_item_quoted(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="PC se apaga poco después de encender",
                    failure_description="Se apaga dos segundos después de encender.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Posible fallo de fuente.",
                    estimated_labor_hours=Decimal("1.00"),
                    required_parts=[
                        PartRequest(search_term="Fuente_Poder", quantity=1)
                    ],
                ),
            ),
        )

        result = invoke(graph, "La PC se apaga al encender.")

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(repository.lookups, ["Fuente_Poder"])
        self.assertEqual(
            [part["code"] for part in result["quote"]["parts"]],
            ["Fuente_Poder"],
        )

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

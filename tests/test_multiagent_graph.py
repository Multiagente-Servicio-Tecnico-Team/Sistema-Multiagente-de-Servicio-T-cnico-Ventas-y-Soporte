import unittest
from decimal import Decimal

from app.agents.jerarquico.graph.builder import build_multiagent_graph
from app.agents.jerarquico.retriever import MarkdownKnowledgeRetriever
from app.agents.jerarquico.schemas import (
    IntakeDecision,
    PartRequest,
    QuoteConfirmation,
    TechnicalDiagnosis,
)
from app.agents.jerarquico.tools.quotes import calculate_quote
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
    def __init__(
        self,
        *,
        customer=True,
        stock=10,
        unit_price=Decimal("10.25"),
        missing_parts=None,
        alternatives=None,
    ) -> None:
        self.customer = (
            {"id": 12, "name": "Ana", "last_name": "Prueba"} if customer else None
        )
        self.stock = stock
        self.unit_price = unit_price
        self.lookups = []
        self.alternative_lookups = []
        self.missing_parts = set(missing_parts or ())
        self.alternatives = list(alternatives or ())
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
        if search_term in self.missing_parts:
            return []
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

    def find_spare_part_alternatives(self, search_term):
        self.alternative_lookups.append(search_term)
        return self.alternatives

    def save_quote(self, **values):
        self.saved_quote = values
        return 91


class AdjustableLaborSettings:
    def __init__(self) -> None:
        self.labor_maintenance_price = Decimal("40.00")
        self.labor_diagnosis_price = Decimal("50.00")

    def require_chat_configuration(self) -> None:
        return None

    def labor_price_for(self, task_type: str) -> Decimal:
        if task_type == "maintenance":
            return self.labor_maintenance_price
        return self.labor_diagnosis_price


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
        labor_maintenance_price=Decimal("40.00"),
        labor_diagnosis_price=Decimal("50.00"),
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
            labor_task_type="maintenance",
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
    def test_hierarchical_package_exports_public_graph_api(self):
        from app.agents.jerarquico import (
            build_multiagent_graph as package_builder,
            calculate_quote as package_calculator,
        )
        from app.agents.jerarquico.graph.builder import (
            build_multiagent_graph as current_builder,
        )
        from app.agents.jerarquico.tools.quotes import (
            calculate_quote as current_calculator,
        )

        self.assertIs(package_builder, current_builder)
        self.assertIs(package_calculator, current_calculator)

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

    def test_calculates_totals_without_floating_point_arithmetic(self):
        quote = calculate_quote(
            labor_cost=Decimal("40.00"),
            labor_task_type="maintenance",
            parts=[
                {
                    "id": 7,
                    "name": "Ventilador",
                    "quantity": 2,
                    "unit_price": Decimal("10.25"),
                }
            ],
        )

        self.assertEqual(quote["labor_cost"], Decimal("40.00"))
        self.assertEqual(quote["parts_cost"], Decimal("20.50"))
        self.assertEqual(quote["total_amount"], Decimal("60.50"))
        self.assertEqual(quote["parts"][0]["subtotal"], Decimal("20.50"))

    def test_diagnosis_quote_allows_fixed_labor_without_parts(self):
        quote = calculate_quote(
            labor_cost=Decimal("50.00"),
            labor_task_type="diagnosis",
            parts=[],
        )

        self.assertEqual(quote["labor_cost"], Decimal("50.00"))
        self.assertEqual(quote["parts_cost"], Decimal("0.00"))
        self.assertEqual(quote["total_amount"], Decimal("50.00"))
        self.assertEqual(quote["parts"], [])

    def test_quote_rejects_zero_price_parts(self):
        with self.assertRaisesRegex(ValueError, "precio positivos"):
            calculate_quote(
                labor_cost=Decimal("40.00"),
                labor_task_type="maintenance",
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
        self.assertIn("el total provisional es S/ 60.50", result["messages"][-1].content)
        self.assertIn(
            "Por lo que describes, podría tratarse de:",
            result["messages"][-1].content,
        )
        self.assertNotIn("Guía consultada", result["messages"][-1].content)
        self.assertNotIn(
            "Orientación técnica preliminar",
            result["messages"][-1].content,
        )

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
        self.assertEqual(repository.saved_quote["total_amount"], Decimal("60.50"))
        self.assertIn("ST-", result["messages"][-1].content)
        self.assertIn("S/ 60.50", result["messages"][-1].content)

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

    def test_fixed_maintenance_price_change_requires_a_new_confirmation(self):
        repository = FakeRepository()
        settings = AdjustableLaborSettings()
        graph = build_multiagent_graph(
            settings=settings,
            repository=repository,
            model=make_model(),
        )

        invoke(graph)
        settings.labor_maintenance_price = Decimal("50.00")
        result = invoke(graph, "Sí, confirma", initial=False)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("cambió", result["messages"][-1].content)
        self.assertIn("el total provisional es S/ 70.50", result["messages"][-1].content)

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

    def test_unknown_manual_case_quotes_diagnostic_fee_without_parts(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Requiere revisión técnica.",
                    labor_task_type="diagnosis",
                    required_parts=[],
                )
            ),
            retriever=MarkdownKnowledgeRetriever(documents=()),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(result["labor_task_type"], "diagnosis")
        self.assertTrue(result["awaiting_quote_confirmation"])
        self.assertEqual(repository.lookups, [])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertEqual(result["quote"]["labor_cost"], Decimal("50.00"))
        self.assertEqual(result["quote"]["parts_cost"], Decimal("0.00"))
        self.assertEqual(result["quote"]["total_amount"], Decimal("50.00"))
        self.assertEqual(result["quote"]["parts"], [])
        self.assertIn("diagnostique la falla", result["messages"][-1].content)
        self.assertIn("S/ 50.00", result["messages"][-1].content)
        self.assertIn("generar un ticket", result["messages"][-1].content)
        self.assertIn("repuestos quedan en S/ 0.00", result["messages"][-1].content)

        result = invoke(graph, "Sí, confirma", initial=False)

        self.assertEqual(result["outcome"], "quoted")
        self.assertEqual(repository.created_ticket["request_type"], "REPAIR")
        self.assertEqual(repository.created_ticket["customer_id"], 12)
        self.assertIsNotNone(repository.saved_quote)
        self.assertEqual(repository.saved_quote["labor_cost"], Decimal("50.00"))
        self.assertEqual(repository.saved_quote["parts_cost"], Decimal("0.00"))
        self.assertEqual(repository.saved_quote["total_amount"], Decimal("50.00"))
        self.assertEqual(repository.saved_quote["parts"], [])
        self.assertIn(
            "Costo fijo de mano de obra: S/ 50.00",
            repository.saved_quote["observations"],
        )
        self.assertIn("diagnóstico: S/ 50.00", result["messages"][-1].content)

    def test_declined_diagnostic_quote_does_not_persist(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                confirmation=QuoteConfirmation(decision="decline"),
            ),
            retriever=MarkdownKnowledgeRetriever(documents=()),
        )

        suggestion = invoke(graph)
        result = invoke(graph, "No, gracias", initial=False)

        self.assertEqual(suggestion["outcome"], "awaiting_confirmation")
        self.assertEqual(result["outcome"], "declined")
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("No guardé el ticket ni la cotización", result["messages"][-1].content)

    def test_unknown_case_does_not_use_model_generated_parts(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(),
            retriever=MarkdownKnowledgeRetriever(documents=()),
        )

        result = invoke(graph)

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(result["required_parts"], [])
        self.assertEqual(repository.lookups, [])
        self.assertIsNone(repository.created_ticket)

    def test_slow_applications_with_unconfirmed_cause_quotes_diagnosis_only(self):
        repository = FakeRepository()
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="Laptop lenta",
                    failure_description="Demora en abrir aplicaciones.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="El almacenamiento podría limitar el rendimiento.",
                    labor_task_type="diagnosis",
                    required_parts=[
                        PartRequest(search_term="SSD_1TB", quantity=1)
                    ],
                ),
            ),
        )

        result = invoke(graph, "Mi laptop está lenta y demora en abrir aplicaciones.")

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(result["labor_task_type"], "diagnosis")
        self.assertEqual(repository.lookups, [])
        self.assertEqual(result["quote"]["labor_cost"], Decimal("50.00"))
        self.assertEqual(result["quote"]["parts_cost"], Decimal("0.00"))
        self.assertEqual(result["quote"]["parts"], [])
        self.assertIn(
            "Laptop lenta y demora en abrir aplicaciones",
            [document["title"] for document in result["rag_documents"]],
        )

        result = invoke(graph, "Sí, guarda el ticket y el presupuesto.", initial=False)

        self.assertEqual(result["outcome"], "quoted")
        self.assertEqual(repository.saved_quote["labor_cost"], Decimal("50.00"))
        self.assertEqual(repository.saved_quote["parts_cost"], Decimal("0.00"))
        self.assertEqual(repository.saved_quote["total_amount"], Decimal("50.00"))
        self.assertEqual(repository.saved_quote["parts"], [])

    def test_suggests_single_in_stock_ssd_capacity_alternative(self):
        repository = FakeRepository(
            missing_parts={"SSD_1TB"},
            alternatives=[
                {
                    "id": 19,
                    "code": "SSD_500GB",
                    "name": "SSD 500 GB",
                    "unit_price": Decimal("45.00"),
                    "current_stock": 3,
                }
            ],
        )
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="Laptop lenta",
                    failure_description="Demora en abrir aplicaciones.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="La unidad está degradada y requiere cambio.",
                    labor_task_type="maintenance",
                    required_parts=[
                        PartRequest(search_term="SSD_1TB", quantity=1)
                    ],
                )
            ),
        )

        result = invoke(graph, "Mi laptop está lenta y demora en abrir aplicaciones.")

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(
            [part["code"] for part in result["quote"]["parts"]],
            ["SSD_500GB"],
        )
        self.assertIn("SSD_1TB", result["inventory_substitutions"][0]["requested_code"])
        self.assertIn(
            "SSD_500GB",
            result["messages"][-1].content,
        )
        answer = result["messages"][-1].content
        self.assertIn("No tenemos disponible SSD_1TB, pero sí", answer)
        self.assertIn("el técnico debe confirmar que sea compatible", answer)
        self.assertNotIn("Guía consultada", answer)
        self.assertNotIn("Orientación técnica preliminar", answer)
        self.assertEqual(answer.count("SSD_500GB"), 1)
        self.assertIsNone(repository.created_ticket)

    def test_lists_multiple_available_same_family_options_without_quoting(self):
        repository = FakeRepository(
            missing_parts={"SSD_1TB"},
            alternatives=[
                {
                    "id": 19,
                    "code": "SSD_500GB",
                    "name": "SSD 500 GB",
                    "unit_price": Decimal("45.00"),
                    "current_stock": 3,
                },
                {
                    "id": 20,
                    "code": "SSD_2TB",
                    "name": "SSD 2 TB",
                    "unit_price": Decimal("90.00"),
                    "current_stock": 1,
                },
            ],
        )
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="Laptop lenta",
                    failure_description="Demora en abrir aplicaciones.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Almacenamiento por revisar.",
                    labor_task_type="maintenance",
                    required_parts=[
                        PartRequest(search_term="SSD_1TB", quantity=1)
                    ],
                )
            ),
        )

        result = invoke(graph, "Mi laptop está lenta y demora en abrir aplicaciones.")

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertIn("SSD_500GB", result["messages"][-1].content)
        self.assertIn("SSD_2TB", result["messages"][-1].content)
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)

    def test_reports_explicitly_when_requested_part_and_alternatives_are_out_of_stock(self):
        repository = FakeRepository(
            missing_parts={"SSD_1TB"},
            alternatives=[
                {
                    "id": 19,
                    "code": "SSD_500GB",
                    "name": "SSD 500 GB",
                    "unit_price": Decimal("45.00"),
                    "current_stock": 0,
                }
            ],
        )
        graph = build_multiagent_graph(
            settings=make_settings(),
            repository=repository,
            model=make_model(
                intake=IntakeDecision(
                    route="service",
                    request_type="REPAIR",
                    title="Laptop lenta",
                    failure_description="Demora en abrir aplicaciones.",
                ),
                diagnosis=TechnicalDiagnosis(
                    provisional_diagnosis="Almacenamiento por revisar.",
                    labor_task_type="maintenance",
                    required_parts=[
                        PartRequest(search_term="SSD_1TB", quantity=1)
                    ],
                )
            ),
        )

        result = invoke(graph, "Mi laptop está lenta y demora en abrir aplicaciones.")

        self.assertEqual(result["outcome"], "inventory_unavailable")
        self.assertIn(
            "No tenemos stock suficiente del repuesto SSD_1TB",
            result["messages"][-1].content,
        )
        self.assertIn("SSD_500GB", result["messages"][-1].content)
        self.assertIn("stock 0", result["messages"][-1].content)
        self.assertIsNone(repository.created_ticket)

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
                    labor_task_type="diagnosis",
                    required_parts=[],
                ),
            ),
        )

        result = invoke(graph, "La PC se apaga al encender.")

        self.assertEqual(result["outcome"], "awaiting_confirmation")
        self.assertEqual(result["labor_task_type"], "diagnosis")
        self.assertEqual(result["quote"]["labor_cost"], Decimal("50.00"))
        self.assertEqual(result["quote"]["parts_cost"], Decimal("0.00"))
        self.assertEqual(repository.lookups, [])
        self.assertIsNone(repository.created_ticket)
        self.assertIsNone(repository.saved_quote)
        self.assertIn("causa exacta", result["messages"][-1].content)

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
                    labor_task_type="maintenance",
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

    def test_settings_reject_unknown_labor_task_type(self):
        with self.assertRaisesRegex(ValueError, "Tipo de trabajo no reconocido"):
            make_settings().labor_price_for("repair")


if __name__ == "__main__":
    unittest.main()

import unittest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app, get_trace_context, redact_trace_error
from app.settings import Settings


class FakeGraph:
    def __init__(self, *, outcome="awaiting_confirmation", stale_ticket=False) -> None:
        self.inputs = []
        self.outcome = outcome
        self.stale_ticket = stale_ticket

    def invoke(self, values, config):
        self.inputs.append((values, config))
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Propuesta indicativa. ¿Confirmas?"
                        if self.outcome == "awaiting_confirmation"
                        else "Ticket y cotización registrados."
                    )
                )
            ],
            "outcome": self.outcome,
            "ticket_id": 84 if self.outcome == "quoted" or self.stale_ticket else None,
            "ticket_code": (
                "ST-123456789ABC"
                if self.outcome == "quoted" or self.stale_ticket
                else None
            ),
            "quote_id": 91 if self.outcome == "quoted" or self.stale_ticket else None,
            "quote": {
                "labor_cost": Decimal("120.00"),
                "parts_cost": Decimal("20.50"),
                "total_amount": Decimal("140.50"),
            },
        }


class ChatApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_serves_chat_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Asistente de servicio técnico", response.text)

    def test_favicon_request_does_not_log_a_missing_resource(self):
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 204)

    def test_chat_returns_indicative_quote_without_ticket_before_confirmation(self):
        graph = FakeGraph()
        session_id = str(uuid4())
        with patch("app.main.get_graph", return_value=graph):
            response = self.client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "email": " ANA@example.com ",
                    "message": " Mi laptop se apaga ",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "awaiting_confirmation")
        self.assertEqual(response.json()["answer"], "Propuesta indicativa. ¿Confirmas?")
        self.assertIsNone(response.json()["ticket_code"])
        self.assertEqual(response.json()["quote"]["total_amount"], "140.50")
        graph_input, graph_config = graph.inputs[0]
        self.assertEqual(set(graph_input), {"messages", "customer_email"})
        self.assertEqual(graph_input["customer_email"], "ana@example.com")
        self.assertEqual(
            graph_config["metadata"],
            {"session_id": session_id},
        )

    def test_chat_returns_ticket_reference_after_confirmation(self):
        graph = FakeGraph(outcome="quoted")
        with patch("app.main.get_graph", return_value=graph):
            response = self.client.post(
                "/api/chat",
                json={
                    "session_id": str(uuid4()),
                    "email": "ana@example.com",
                    "message": "Sí, confirma",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "quoted")
        self.assertEqual(response.json()["ticket_code"], "ST-123456789ABC")
        self.assertEqual(response.json()["quote_id"], 91)
        self.assertEqual(response.json()["quote"]["total_amount"], "140.50")

    def test_chat_hides_persisted_ticket_ids_for_nonquoted_outcomes(self):
        graph = FakeGraph(stale_ticket=True)
        with patch("app.main.get_graph", return_value=graph):
            response = self.client.post(
                "/api/chat",
                json={
                    "session_id": str(uuid4()),
                    "email": "ana@example.com",
                    "message": "Mi laptop se calienta",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "awaiting_confirmation")
        self.assertIsNone(response.json()["ticket_id"])
        self.assertIsNone(response.json()["ticket_code"])
        self.assertIsNone(response.json()["quote_id"])

    def test_chat_does_not_reset_checkpointed_fields_on_followup(self):
        graph = FakeGraph()
        session_id = str(uuid4())
        with patch("app.main.get_graph", return_value=graph):
            for message in ("Mi laptop se calienta y se apaga", "Sí, confirma"):
                response = self.client.post(
                    "/api/chat",
                    json={
                        "session_id": session_id,
                        "email": "ana@example.com",
                        "message": message,
                    },
                )
                self.assertEqual(response.status_code, 200)

        followup_values = graph.inputs[1][0]
        self.assertEqual(
            set(followup_values),
            {"messages", "customer_email"},
        )

    def test_rejects_reusing_session_for_another_email(self):
        graph = FakeGraph()
        session_id = str(uuid4())
        with patch("app.main.get_graph", return_value=graph):
            first = self.client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "email": "ana@example.com",
                    "message": "Necesito soporte",
                },
            )
            second = self.client.post(
                "/api/chat",
                json={
                    "session_id": session_id,
                    "email": "otra@example.com",
                    "message": "Ver cotización",
                },
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(len(graph.inputs), 1)

    def test_rejects_invalid_email_and_blank_message(self):
        graph = FakeGraph()
        with patch("app.main.get_graph", return_value=graph):
            invalid_email = self.client.post(
                "/api/chat",
                json={
                    "session_id": str(uuid4()),
                    "email": "invalid",
                    "message": "Hola",
                },
            )
            blank_message = self.client.post(
                "/api/chat",
                json={
                    "session_id": str(uuid4()),
                    "email": "ana@example.com",
                    "message": "  ",
                },
            )

        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(blank_message.status_code, 422)
        self.assertEqual(graph.inputs, [])

    def test_reports_missing_runtime_configuration(self):
        with patch(
            "app.main.get_graph",
            side_effect=RuntimeError("Falta configurar GROQ_API_KEY."),
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "session_id": str(uuid4()),
                    "email": "ana@example.com",
                    "message": "Necesito soporte",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("GROQ_API_KEY", response.json()["detail"])

    def test_langsmith_context_redacts_trace_inputs_and_outputs(self):
        settings = Settings(
            groq_api_key="test-key",
            groq_model="test-model",
            database_url="postgresql+pg8000://localhost/test",
            langsmith_api_key="test-tracing-key",
            langsmith_tracing=True,
            langsmith_project="test-project",
            langsmith_hide_inputs=True,
            langsmith_hide_outputs=True,
            labor_hourly_rate=Decimal("80.00"),
        )
        with (
            patch("app.main.load_settings", return_value=settings),
            patch("app.main.Client") as client_factory,
            patch("app.main.tracing_context") as tracing_factory,
        ):
            trace_context = get_trace_context()

        client_factory.assert_called_once_with(
            api_key="test-tracing-key",
            hide_inputs=True,
            hide_outputs=True,
            anonymizer=redact_trace_error,
        )
        tracing_factory.assert_called_once_with(
            enabled=True,
            project_name="test-project",
            client=client_factory.return_value,
        )
        self.assertIs(trace_context, tracing_factory.return_value)

    def test_langsmith_anonymizer_redacts_provider_error_details(self):
        error = "Groq failed_generation contains generated response text."

        redacted = redact_trace_error(
            {"error": error, "run_type": "llm"}
        )

        self.assertNotIn(error, redacted["error"])
        self.assertIn("redacted", redacted["error"])
        self.assertEqual(redacted["run_type"], "llm")


if __name__ == "__main__":
    unittest.main()

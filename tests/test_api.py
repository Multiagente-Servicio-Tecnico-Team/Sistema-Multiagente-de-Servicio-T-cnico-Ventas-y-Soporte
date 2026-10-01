import unittest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app


class FakeGraph:
    def __init__(self) -> None:
        self.inputs = []

    def invoke(self, values, config):
        self.inputs.append((values, config))
        return {
            "messages": [AIMessage(content="Ticket y cotización registrados.")],
            "outcome": "quoted",
            "ticket_id": 84,
            "ticket_code": "ST-123456789ABC",
            "quote_id": 91,
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

    def test_chat_returns_answer_and_quote(self):
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
        self.assertEqual(response.json()["answer"], "Ticket y cotización registrados.")
        self.assertEqual(response.json()["ticket_code"], "ST-123456789ABC")
        self.assertEqual(response.json()["quote"]["total_amount"], "140.50")
        graph_input, graph_config = graph.inputs[0]
        self.assertEqual(graph_input["customer_email"], "ana@example.com")
        self.assertEqual(graph_input["outcome"], "pending")
        self.assertEqual(
            graph_config["metadata"],
            {"session_id": session_id},
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


if __name__ == "__main__":
    unittest.main()

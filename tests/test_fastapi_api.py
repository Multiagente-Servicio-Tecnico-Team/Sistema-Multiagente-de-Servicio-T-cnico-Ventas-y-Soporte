import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.web import app
from app.agents.orquestador.knowledge import retrieve_faq
from langchain_core.messages import HumanMessage


class FastApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_root_opens_email_login_screen(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn('id="email"', response.text)
        self.assertIn("/api/v1/users/identify", response.text)
        self.assertIn("/api/v1/chat", response.text)

    def test_faq_retriever_finds_payment_and_location_topics(self):
        self.assertIn("Medios de pago", retrieve_faq("¿Qué medios de pago aceptan?")[0])
        self.assertIn("Ubicación", retrieve_faq("¿Dónde queda la tienda?")[0])

    def test_attention_answers_faq_from_rag_without_creating_ticket(self):
        from app.agents.orquestador.agentes.customer_service import customer_service_node

        fake_model = unittest.mock.Mock()
        fake_model.invoke.return_value.content = "El horario de referencia es de lunes a sábado."
        with patch("app.agents.orquestador.agentes.customer_service._model", return_value=fake_model), patch(
            "app.agents.orquestador.agentes.customer_service.create_ticket"
        ) as create_ticket:
            result = customer_service_node({"messages": [HumanMessage(content="¿Cuál es el horario de atención?")]})

        self.assertEqual(result["intent"], "INFO_QUERY")
        self.assertFalse(result.get("ticket_id"))
        create_ticket.assert_not_called()
        self.assertIn("horario", fake_model.invoke.call_args.args[0][0]["content"].casefold())

    def test_warranty_status_questions_are_not_captured_as_generic_faq(self):
        from app.agents.orquestador.agentes.customer_service import _is_clear_faq

        self.assertFalse(_is_clear_faq("¿Sigue vigente la garantía WAR-SALE-3301?"))

    def test_identify_returns_database_user_id(self):
        with patch("app.web.find_user_by_email", return_value={"id": 123, "name": "Cliente Demo"}):
            response = self.client.post("/api/v1/users/identify", json={"email": "demo@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], 123)
        self.assertIn("thread_id", response.json())

    def test_chat_rejects_user_not_bound_to_session(self):
        response = self.client.post("/api/v1/chat", json={"user_id": 123, "thread_id": "a" * 32, "message": "Hola"})
        self.assertEqual(response.status_code, 401)

    def test_chat_invokes_graph_for_authenticated_session(self):
        with patch("app.web.find_user_by_email", return_value={"id": 123, "name": "Cliente Demo"}):
            session = self.client.post("/api/v1/users/identify", json={"email": "demo@example.com"}).json()
        expected = {"response": "Te ayudo.", "ticket_id": None}
        with patch("app.web._agent_graph") as graph_factory:
            graph_factory.return_value.invoke.return_value = expected
            response = self.client.post("/api/v1/chat", json={"user_id": 123, "thread_id": session["thread_id"], "message": "Hola"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Te ayudo.")
        graph_factory.return_value.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()

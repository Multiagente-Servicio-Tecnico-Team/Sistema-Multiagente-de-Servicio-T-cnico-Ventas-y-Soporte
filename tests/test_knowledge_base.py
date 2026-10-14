import unittest

from app.agents.orquestador.knowledge import retrieve_faq, retrieve_technical_knowledge


class TechnicalKnowledgeTests(unittest.TestCase):
    def test_retrieves_matching_thermal_failure(self):
        passages = retrieve_technical_knowledge(
            "laptop HP se calienta y se apaga con ventilador ruidoso"
        )

        self.assertTrue(passages)
        self.assertIn("Sobrecalentamiento", passages[0])
        self.assertIn("ventilador", passages[0].casefold())

    def test_retrieval_normalizes_accents(self):
        passages = retrieve_technical_knowledge("batería no carga y dura poco")

        self.assertTrue(passages)
        self.assertIn("Bateria no carga", passages[0])

    def test_returns_no_context_for_unrelated_query(self):
        self.assertEqual(retrieve_technical_knowledge("impresora no escanea"), [])

    def test_faq_rag_uses_atencion_document_for_shop_services_and_policies(self):
        self.assertIn("Ubicación", retrieve_faq("¿Dónde queda la tienda?")[0])
        self.assertIn("Medios de pago", retrieve_faq("¿Qué medios de pago aceptan?")[0])
        self.assertTrue(any("garantía" in p.casefold() for p in retrieve_faq("¿Cuál es la duración de garantía?")))

    def test_faq_rag_retrieves_hours_and_services(self):
        hours = retrieve_faq("¿Cuál es el horario de atención?")
        services = retrieve_faq("¿Qué servicio ofrecen?")

        self.assertTrue(any("Horarios" in p for p in hours))
        self.assertTrue(any("Servicios" in p for p in services))

    def test_faq_retriever_does_not_use_agent_prompt_docs(self):
        from app.agents.orquestador.knowledge.retriever import ROOT

        self.assertTrue((ROOT / "atencion.md").exists())
        self.assertFalse((ROOT / "preguntas_frecuentes.md").exists())


if __name__ == "__main__":
    unittest.main()

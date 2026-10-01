import unittest

from app.agents.retriever import SimulatedKnowledgeRetriever


class SimulatedKnowledgeRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.retriever = SimulatedKnowledgeRetriever()

    def test_recovers_storage_case_from_spanish_symptoms(self):
        results = self.retriever.retrieve(
            "Mi laptop está lenta y tarda mucho en arrancar"
        )

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "CASE-LAPTOP-SLOW-STORAGE-01")
        self.assertEqual(results[0].recommended_parts[0].code, "REP-SSD-500GB")

    def test_recovers_battery_case_across_accents_and_synonyms(self):
        results = self.retriever.retrieve("la bateria no retiene carga")

        self.assertEqual(results[0].id, "CASE-LAPTOP-BATTERY-01")
        self.assertEqual(results[0].recommended_parts[0].code, "REP-BAT-L2023")

    def test_no_unrelated_documents_are_returned(self):
        self.assertEqual(
            self.retriever.retrieve("consulta sobre horario de atención"),
            [],
        )

    def test_retrieved_context_marks_costs_as_simulated(self):
        document = self.retriever.retrieve("memoria ram insuficiente")[0]
        context = self.retriever.format_context([document])

        self.assertIn("REP-RAM-16GB", context)
        self.assertIn("SIMULADO", context)
        self.assertIn("no es un precio real", context)

    def test_limit_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            self.retriever.retrieve("bateria", limit=0)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from app.settings import Settings, load_settings


class SettingsTests(unittest.TestCase):
    def load_from_environment(self, values: dict[str, str]) -> Settings:
        with patch.dict(os.environ, values, clear=True):
            with patch("app.settings.load_dotenv"):
                return load_settings()

    def test_loads_agent_database_and_tracing_settings(self):
        settings = self.load_from_environment(
            {
                "GROQ_API_KEY": "groq-secret",
                "GROQ_MODEL": "test-model",
                "DATABASE_URL": "postgresql+pg8000://user:password@localhost/db",
                "LANGSMITH_API_KEY": "langsmith-secret",
                "LANGSMITH_TRACING": "true",
                "LABOR_HOURLY_RATE": "75.50",
            }
        )

        self.assertEqual(settings.groq_model, "test-model")
        self.assertTrue(settings.langsmith_tracing)
        self.assertTrue(settings.langsmith_hide_inputs)
        self.assertTrue(settings.langsmith_hide_outputs)
        self.assertEqual(settings.labor_hourly_rate, Decimal("75.50"))
        settings.require_chat_configuration()

    def test_missing_tracing_key_is_reported(self):
        settings = self.load_from_environment(
            {
                "GROQ_API_KEY": "groq-secret",
                "GROQ_MODEL": "test-model",
                "DATABASE_URL": "postgresql+pg8000://localhost/db",
                "LANGSMITH_TRACING": "true",
            }
        )

        with self.assertRaisesRegex(RuntimeError, "LANGSMITH_API_KEY"):
            settings.require_chat_configuration()

    def test_langsmith_trace_redaction_can_be_explicitly_disabled(self):
        settings = self.load_from_environment(
            {
                "LANGSMITH_HIDE_INPUTS": "false",
                "LANGSMITH_HIDE_OUTPUTS": "false",
            }
        )

        self.assertFalse(settings.langsmith_hide_inputs)
        self.assertFalse(settings.langsmith_hide_outputs)

    def test_sensitive_settings_are_not_in_repr(self):
        settings = self.load_from_environment(
            {
                "GROQ_API_KEY": "groq-secret",
                "GROQ_MODEL": "test-model",
                "DATABASE_URL": "postgresql+pg8000://user:password@localhost/db",
                "LANGSMITH_API_KEY": "langsmith-secret",
            }
        )

        rendered = repr(settings)
        self.assertNotIn("groq-secret", rendered)
        self.assertNotIn("langsmith-secret", rendered)
        self.assertNotIn("password", rendered)

    def test_labor_rate_must_be_configured_for_quotes(self):
        settings = self.load_from_environment({})

        with self.assertRaisesRegex(RuntimeError, "LABOR_HOURLY_RATE"):
            settings.require_labor_hourly_rate()

    def test_rejects_negative_labor_rate(self):
        with self.assertRaisesRegex(ValueError, "no negativo"):
            self.load_from_environment({"LABOR_HOURLY_RATE": "-1"})

    def test_rejects_invalid_tracing_flag(self):
        with self.assertRaisesRegex(ValueError, "LANGSMITH_TRACING"):
            self.load_from_environment({"LANGSMITH_TRACING": "sometimes"})


if __name__ == "__main__":
    unittest.main()

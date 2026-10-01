import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = field(repr=False)
    groq_model: str | None
    database_url: str | None = field(repr=False)
    langsmith_api_key: str | None = field(repr=False)
    langsmith_tracing: bool
    langsmith_project: str
    langsmith_hide_inputs: bool
    langsmith_hide_outputs: bool
    labor_hourly_rate: Decimal | None

    def require_chat_configuration(self) -> None:
        missing = []
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if not self.groq_model:
            missing.append("GROQ_MODEL")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if self.langsmith_tracing and not self.langsmith_api_key:
            missing.append("LANGSMITH_API_KEY (requerida con LANGSMITH_TRACING=true)")
        if missing:
            raise RuntimeError(
                "Falta configurar: " + ", ".join(missing) + ". "
                "Revisa las variables del archivo .env."
            )

    def require_labor_hourly_rate(self) -> Decimal:
        if self.labor_hourly_rate is None:
            raise RuntimeError(
                "LABOR_HOURLY_RATE no está configurada; no se puede generar "
                "una cotización sin una tarifa definida."
            )
        return self.labor_hourly_rate


def _optional_decimal(name: str) -> Decimal | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} debe ser un importe decimal válido.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{name} debe ser un importe decimal no negativo.")
    return amount


def _environment_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"{name} debe ser true o false.")


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip() or None,
        groq_model=os.getenv("GROQ_MODEL", "").strip() or None,
        database_url=os.getenv("DATABASE_URL", "").strip() or None,
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY", "").strip() or None,
        langsmith_tracing=_environment_flag("LANGSMITH_TRACING", default=False),
        langsmith_project=os.getenv(
            "LANGSMITH_PROJECT",
            "Sistema-Multiagente-de-Servicio-Tecnico-Ventas-y-Soporte",
        ).strip(),
        langsmith_hide_inputs=_environment_flag(
            "LANGSMITH_HIDE_INPUTS",
            default=True,
        ),
        langsmith_hide_outputs=_environment_flag(
            "LANGSMITH_HIDE_OUTPUTS",
            default=True,
        ),
        labor_hourly_rate=_optional_decimal("LABOR_HOURLY_RATE"),
    )

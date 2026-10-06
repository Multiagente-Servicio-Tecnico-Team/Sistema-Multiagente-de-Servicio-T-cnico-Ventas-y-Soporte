import os

from dotenv import load_dotenv


load_dotenv()
CURRENCY = os.getenv("CURRENCY", "COP").upper()


def configure_tracing() -> None:
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "true").lower()
    os.environ["LANGSMITH_TRACING"] = tracing_enabled
    os.environ["LANGCHAIN_TRACING_V2"] = tracing_enabled
    os.environ.setdefault(
        "LANGSMITH_PROJECT",
        "Sistema-Multiagente-de-Servicio-Tecnico-Ventas-y-Soporte",
    )


def create_chat_model():
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Agrega GROQ_API_KEY al archivo .env para iniciar los agentes")

    configure_tracing()
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        api_key=api_key,
    )
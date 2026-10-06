"""Configuración común: las pruebas de tests/ no dependen de servicios externos."""
import os

import pytest

GROQ_REAL = bool(os.getenv("GROQ_API_KEY"))

# Los agentes de la red descentralizada crean ChatGroq al importarse; las pruebas unitarias no llaman al modelo.
os.environ.setdefault("GROQ_API_KEY", "clave-de-prueba-sin-red")


def pytest_collection_modifyitems(config, items):
    if GROQ_REAL:
        return
    omitir = pytest.mark.skip(reason="Requiere GROQ_API_KEY real y conexión a Internet")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(omitir)

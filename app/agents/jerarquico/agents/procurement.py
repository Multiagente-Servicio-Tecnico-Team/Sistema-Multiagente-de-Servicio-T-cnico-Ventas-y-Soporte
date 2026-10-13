from typing import Any

from langchain_core.messages import AIMessage

from app.agents.jerarquico.graph.state import ServiceState


def purchasing_agent(state: ServiceState) -> dict[str, Any]:
    return {
        "outcome": "procurement_unavailable",
        "messages": [
            AIMessage(
                content=(
                    "El catálogo no tiene stock suficiente. La base de proveedores "
                    "no relaciona proveedores con productos ni contiene cotizaciones "
                    "de costo; por eso no puedo confirmar una compra, un precio ni "
                    "un plazo. No se reservó inventario."
                )
            )
        ],
    }

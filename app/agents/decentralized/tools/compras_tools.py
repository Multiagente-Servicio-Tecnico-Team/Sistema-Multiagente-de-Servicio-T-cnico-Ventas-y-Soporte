"""Abastecimiento consultivo sin integraciones externas ni escrituras SQL."""
from langchain_core.tools import tool
from app.agents.decentralized.tools.soporte_tools import transferir_a_ventas as _ventas


@tool
def consultar_fuentes_abastecimiento() -> dict:
    """Informa capacidades reales: no hay una fuente de ofertas conectada."""
    return {"integration_available": False,
            "missing_fields": ["proveedor asociado verificado", "oferta vigente", "costo", "moneda", "plazo confirmado"]}


@tool
def transferir_a_ventas(motivo: str) -> str:
    """Entrega limitaciones de abastecimiento a Ventas; no confirma compras."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Motivo de transferencia obligatorio")
    return _ventas.invoke({"motivo": motivo.strip()})

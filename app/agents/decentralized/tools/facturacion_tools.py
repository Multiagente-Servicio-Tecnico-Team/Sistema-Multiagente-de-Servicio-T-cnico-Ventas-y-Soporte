"""Financial handoffs and actual capabilities; no commercial write tools enabled."""
from langchain_core.tools import tool
from app.agents.decentralized.tools.software_tools import transferir_a_soporte as _soporte
from app.agents.decentralized.tools.soporte_tools import transferir_a_ventas as _ventas


@tool
def transferir_a_facturacion(motivo: str) -> str:
    """Consulta financiera; no crea pagos ni acredita aceptación o pago recibido."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Motivo obligatorio")
    return f"TRANSFERIR_FACTURACION: {motivo.strip()}"


@tool
def transferir_a_soporte(motivo: str) -> str:
    """Solicita atención administrativa sin confirmar un pago ni emitir factura."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Motivo obligatorio")
    return _soporte.invoke({"motivo": motivo.strip()})


@tool
def transferir_a_ventas(motivo: str) -> str:
    """Devuelve una propuesta pendiente o incompatible a Ventas."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Motivo obligatorio")
    return _ventas.invoke({"motivo": motivo.strip()})


@tool
def consultar_capacidades_financieras() -> dict:
    """Informa integraciones financieras habilitadas, sin ejecutar operaciones."""
    return {"payment_write_enabled": False, "fiscal_integration_available": False,
            "payment_reconciliation_available": False, "refund_write_enabled": False}

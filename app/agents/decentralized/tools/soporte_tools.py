from langchain_core.tools import tool


@tool
def transferir_a_soporte(motivo: str) -> str:
    """Devuelve a Soporte una consulta de ticket o atención general.

    No registra citas ni solicitudes: solamente transfiere la conversación.
    """
    return f"TRANSFERIR_SOPORTE: {motivo}"


@tool #decorador de python
def consultar_estado_ticket(numero_ticket: int) -> str:
    """
    Consulta el estado de un ticket de soporte utilizando su número.
    """
    
    # Datos simulados temporalmente
    tickets = {
        1001: "En revisión",
        1002: "Derivado al área técnica",
        1003: "Resuelto"
    }

    estado = tickets.get(numero_ticket)

    if estado:
        return f"El ticket {numero_ticket} se encuentra: {estado}"

    return f"No se encontró el ticket {numero_ticket}"

@tool
def transferir_a_tecnico(motivo: str) -> str:
    """
    Transfiere una solicitud al agente Técnico cuando el problema
    requiere diagnóstico o conocimientos técnicos especializados.
    """
    return f"TRANSFERIR_TECNICO: {motivo}"

@tool
def transferir_a_ventas(motivo: str) -> str:
    """
    Transfiere una solicitud al agente de Ventas cuando el usuario
    requiere información comercial, precios o cotizaciones.
    """
    return f"TRANSFERIR_VENTAS: {motivo}"

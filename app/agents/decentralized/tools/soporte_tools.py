from langchain_core.tools import tool


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
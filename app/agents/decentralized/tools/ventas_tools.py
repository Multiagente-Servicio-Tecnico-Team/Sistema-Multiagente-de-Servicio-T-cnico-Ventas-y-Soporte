import unicodedata
from langchain_core.tools import tool


def normalizar_servicio(servicio: str) -> str:
    servicio = servicio.lower().strip()

    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", servicio)
        if unicodedata.category(caracter) != "Mn"
    )


@tool
def generar_cotizacion(servicio: str) -> str:
    """
    Identifica el servicio solicitado sin inventar tarifas.

    Los precios de repuestos deben provenir de PostgreSQL.
    La mano de obra requiere una tarifa verificada.
    """

    servicio_normalizado = normalizar_servicio(servicio)

    servicios = (
        "diagnostico",
        "mantenimiento",
        "reparacion",
        "instalacion",
    )

    for servicio_conocido in servicios:
        if servicio_conocido in servicio_normalizado:
            return (
                f"Servicio: {servicio_conocido}. "
                "Tarifa de mano de obra pendiente de validacion. "
                "No se puede confirmar un precio total."
            )

    return (
        "No se encontro una cotizacion para el servicio solicitado. "
        "Se requiere evaluacion comercial."
    )


@tool
def transferir_a_tecnico(motivo: str) -> str:
    """
    Transfiere una solicitud al agente Tecnico cuando
    requiere diagnostico especializado.
    """

    return f"TRANSFERIR_TECNICO: {motivo}"
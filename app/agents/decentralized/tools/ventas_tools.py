import unicodedata
from langchain_core.tools import tool


@tool
def generar_cotizacion(servicio: str) -> str:
    """
    Genera una cotización preliminar según el servicio solicitado.
    """

    # Precios simulados temporalmente
    servicios = {
        "diagnostico": 50,
        "mantenimiento": 80,
        "reparacion": 120,
        "instalacion": 70,
    }

    # Convertimos el texto a minúsculas y eliminamos espacios
    servicio_normalizado = servicio.lower().strip()

    # Eliminamos tildes para facilitar la comparación
    servicio_normalizado = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", servicio_normalizado)
        if unicodedata.category(caracter) != "Mn"
    )

    # Buscamos el servicio dentro de la descripción recibida
    for servicio_conocido, precio in servicios.items():
        if servicio_conocido in servicio_normalizado:
            return (
                f"Servicio: {servicio_conocido}. "
                f"Precio estimado: S/ {precio}."
            )

    return (
        "No se encontró una cotización para el servicio solicitado. "
        "Se requiere evaluación comercial."
    )
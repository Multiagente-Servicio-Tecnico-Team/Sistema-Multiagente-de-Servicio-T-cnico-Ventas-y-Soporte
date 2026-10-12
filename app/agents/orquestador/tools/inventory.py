from langchain_core.tools import tool

from app.database.repository import lookup_inventory


@tool
def consultar_inventario(nombre_repuesto: str, cantidad: int = 1) -> dict[str, object]:
    """Consulta existencias y precio actual de un repuesto en PostgreSQL."""
    item = lookup_inventory(nombre_repuesto, cantidad)
    item["unit_price"] = str(item["unit_price"])
    return item
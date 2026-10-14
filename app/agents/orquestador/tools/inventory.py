from langchain_core.tools import tool

from app.database.repository import search_inventory_options


@tool
def consultar_inventario(consulta: str) -> list[dict]:
    """Busca componentes activos por nombre, código, categoría o especificación en PostgreSQL."""
    return search_inventory_options(consulta)

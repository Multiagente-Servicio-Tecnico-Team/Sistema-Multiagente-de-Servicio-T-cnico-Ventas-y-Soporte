from langchain_core.tools import tool


@tool
def diagnosticar_problema(sintoma: str) -> str:
    """
    Realiza un diagnóstico preliminar a partir del síntoma
    reportado por el usuario.
    """

    # Diagnósticos simulados temporalmente
    diagnosticos = {
        "no enciende": (
            "Posible falla en la fuente de alimentación. "
            "Se recomienda revisar la fuente y el cable de energía."
        ),
        "se apaga": (
            "Posible problema de temperatura o alimentación. "
            "Se recomienda revisar ventilación y fuente de poder."
        ),
        "pantalla azul": (
            "Posible problema de memoria RAM, controladores o sistema operativo."
        ),
        "esta lento": (
            "Posible saturación de recursos, almacenamiento lleno "
            "o procesos ejecutándose en segundo plano."
        ),
    }

    sintoma_normalizado = sintoma.lower().strip()

    # Buscamos si alguno de los síntomas conocidos aparece
    # dentro de la descripción enviada por el usuario.
    for sintoma_conocido, diagnostico in diagnosticos.items():
        if sintoma_conocido in sintoma_normalizado:
            return diagnostico

    return (
        "No se encontró un diagnóstico preliminar para el síntoma indicado. "
        "Se requiere una revisión técnica más detallada."
    )

@tool
def transferir_a_ventas(motivo: str) -> str:
    """
    Transfiere una solicitud al agente de Ventas cuando el usuario
    requiere información sobre precios o una cotización.
    """
    return f"TRANSFERIR_VENTAS: {motivo}"

@tool
def transferir_a_almacen(
    motivo: str,
    nombre_repuesto: str,
    cantidad: int = 1,
) -> dict:
    """
    Solicita verificar un repuesto identificado
    para una reparación.

    nombre_repuesto: nombre exacto del repuesto.
    cantidad: unidades requeridas.
    """

    if not nombre_repuesto.strip():
        return {
            "error": "El nombre del repuesto es obligatorio."
        }

    if type(cantidad) is not int or cantidad <= 0:
        return {
            "error": "La cantidad debe ser un entero positivo."
        }

    return {
        "accion": "TRANSFERIR_ALMACEN",
        "motivo": motivo,
        "nombre_repuesto": nombre_repuesto.strip(),
        "cantidad": cantidad,
    }
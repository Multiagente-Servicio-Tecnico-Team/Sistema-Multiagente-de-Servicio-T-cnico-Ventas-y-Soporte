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
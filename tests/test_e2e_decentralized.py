import pytest

from langchain_core.messages import HumanMessage, ToolMessage
from app.agents.decentralized.graph import graph

@pytest.mark.e2e
def test_flujo_soporte_tecnico_ventas():
    """
    Comprueba un flujo real:
    Soporte -> Técnico -> Ventas.

    Utiliza Groq, por lo que requiere conexión
    a Internet y una API key válida.
    """

    estado = {
        "messages": [
            HumanMessage(
                content=(
                    "Mi computadora no enciende. "
                    "Necesito un diagnóstico y también "
                    "una cotización para repararla."
                )
            )
        ],
        "handoff_count": 0,
        "handoff_history": [],
        "errors": [],
    }

    resultado = graph.invoke(
        estado,
        config={"recursion_limit": 30},
    )

    # 1. No deben registrarse errores
    assert resultado.get("errors", []) == []

    # 2. Verificar las transferencias
    assert resultado["handoff_history"] == [
        {"origen": "soporte", "destino": "tecnico"},
        {"origen": "tecnico", "destino": "ventas"},
    ]

    assert resultado["handoff_count"] == 2

    # 3. Recuperar las herramientas ejecutadas
    herramientas = [
        mensaje.name
        for mensaje in resultado["messages"]
        if isinstance(mensaje, ToolMessage)
    ]

    # 4. Verificar diagnóstico y cotización
    assert "diagnosticar_problema" in herramientas
    assert "generar_cotizacion" in herramientas

    # 5. Comprobar el precio simulado
    cotizaciones = [
        mensaje.content
        for mensaje in resultado["messages"]
        if isinstance(mensaje, ToolMessage)
        and mensaje.name == "generar_cotizacion"
    ]

    assert any(
        "S/ 120" in cotizacion
        for cotizacion in cotizaciones
    )

    # 6. Verificar respuesta final
    respuesta_final = resultado["messages"][-1]

    assert respuesta_final.content.strip()

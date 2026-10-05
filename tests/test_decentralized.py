import pytest

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)

from app.agents.decentralized.graph import (
    detectar_handoff,
    registrar_handoff,
    route_next_agent,
    MAX_HANDOFFS,
)

# TEST 1: DETECCIÓN DE TRANSFERENCIAS
def test_detectar_handoff_tecnico():
    mensajes = [
        ToolMessage(
            content="TRANSFERIR_TECNICO: Problema",
            name="transferir_a_tecnico",
            tool_call_id="test-1",
        )
    ]

    assert detectar_handoff(mensajes) == "tecnico"

# TEST 2: TRANSFERENCIA A VENTAS
def test_detectar_handoff_ventas():
    mensajes = [
        ToolMessage(
            content="TRANSFERIR_VENTAS: Precio",
            name="transferir_a_ventas",
            tool_call_id="test-2",
        )
    ]

    assert detectar_handoff(mensajes) == "ventas"

# TEST 3: REGISTRO DEL HISTORIAL
def test_registrar_handoff():
    estado = {
        "messages": [
            ToolMessage(
                content="TRANSFERIR_VENTAS: Cotización",
                name="transferir_a_ventas",
                tool_call_id="test-3",
            )
        ],
        "handoff_count": 0,
        "handoff_history": [],
        "errors": [],
    }

    resultado = registrar_handoff(estado, "soporte")

    assert resultado["next_agent"] == "ventas"
    assert resultado["handoff_count"] == 1
    assert resultado["handoff_history"] == [
        {"origen": "soporte", "destino": "ventas"}
    ]


# TEST 4: LÍMITE DE TRANSFERENCIAS

def test_limite_handoffs():
    estado = {
        "messages": [
            ToolMessage(
                content="TRANSFERIR_TECNICO: Problema",
                name="transferir_a_tecnico",
                tool_call_id="test-4",
            )
        ],
        "handoff_count": MAX_HANDOFFS,
        "handoff_history": [],
        "errors": [],
    }

    resultado = registrar_handoff(estado, "soporte")

    assert resultado["next_agent"] == "finalizar"
    assert resultado["errors"]
    assert any(
        isinstance(mensaje, AIMessage)
        for mensaje in resultado["messages"]
    )


# TEST 5: ENRUTAMIENTO

def test_route_next_agent():
    estado = {
        "messages": [],
        "next_agent": "ventas",
    }

    assert route_next_agent(estado) == "ventas"


# TEST 6: SIN TRANSFERENCIA

def test_sin_handoff():
    mensajes = [
        ToolMessage(
            content="Servicio: mantenimiento",
            name="generar_cotizacion",
            tool_call_id="test-6",
        )
    ]

    assert detectar_handoff(mensajes) is None

def test_error_groq_ventas(monkeypatch):
    from langchain_core.messages import HumanMessage
    from app.agents.decentralized import ventas

    # Simulamos un modelo que falla
    class ModeloFallido:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("API no disponible")

    # Reemplazamos temporalmente el modelo
    monkeypatch.setattr(
        ventas,
        "ventas_llm",
        ModeloFallido()
    )

    estado = {
        "messages": [
            HumanMessage(
                content="¿Cuánto cuesta el mantenimiento?"
            )
        ],
        "errors": [],
    }

    resultado = ventas.ventas_node(estado)

    assert resultado["current_agent"] == "ventas"
    assert resultado["errors"]
    assert "RuntimeError" in resultado["errors"][0]
    assert "No fue posible" in resultado["messages"][0].content

def test_error_groq_soporte(monkeypatch):
    from langchain_core.messages import HumanMessage
    from app.agents.decentralized import soporte

    # Simulamos un modelo que falla
    class ModeloFallido:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("API no disponible")

    monkeypatch.setattr(
        soporte,
        "soporte_llm",
        ModeloFallido()
    )

    estado = {
        "messages": [
            HumanMessage(
                content="Necesito ayuda con mi computadora"
            )
        ],
        "errors": [],
    }

    resultado = soporte.soporte_node(estado)

    assert resultado["current_agent"] == "soporte"
    assert resultado["errors"]
    assert "RuntimeError" in resultado["errors"][0]
    assert "No fue posible" in resultado["messages"][0].content


def test_error_groq_tecnico(monkeypatch):
    from langchain_core.messages import HumanMessage
    from app.agents.decentralized import tecnico

    # Simulamos un modelo que falla
    class ModeloFallido:
        def invoke(self, *args, **kwargs):
            raise RuntimeError("API no disponible")

    monkeypatch.setattr(
        tecnico,
        "tecnico_llm",
        ModeloFallido()
    )

    estado = {
        "messages": [
            HumanMessage(
                content="Mi computadora no enciende"
            )
        ],
        "errors": [],
    }

    resultado = tecnico.tecnico_node(estado)

    assert resultado["current_agent"] == "tecnico"
    assert resultado["errors"]
    assert "RuntimeError" in resultado["errors"][0]
    assert "No fue posible" in resultado["messages"][0].content


def test_error_herramienta():
    from langchain_core.tools import tool
    from langchain_core.messages import AIMessage
    from langgraph.prebuilt import ToolNode
    from langgraph.graph import StateGraph, START, END
    from app.agents.decentralized.state import AgentState

    # Herramienta que falla intencionalmente
    @tool
    def herramienta_fallida(valor: str) -> str:
        """Herramienta que simula un error."""
        raise RuntimeError("Fallo simulado")

    # Creamos el nodo de herramientas
    nodo = ToolNode(
        [herramienta_fallida],
        handle_tool_errors=True
    )

    # Construimos un grafo mínimo
    builder = StateGraph(AgentState)

    builder.add_node("herramientas", nodo)

    builder.add_edge(START, "herramientas")
    builder.add_edge("herramientas", END)

    grafo = builder.compile()

    # Simulamos una llamada a la herramienta
    estado = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "herramienta_fallida",
                        "args": {"valor": "prueba"},
                        "id": "call-test"
                    }
                ]
            )
        ]
    }

    # Ejecutamos el grafo
    resultado = grafo.invoke(estado)

    # Obtenemos el mensaje generado
    mensaje = resultado["messages"][-1]

    # Verificamos que se capturó el error
    assert mensaje.status == "error"
    assert mensaje.tool_call_id == "call-test"
    assert "RuntimeError" in mensaje.content

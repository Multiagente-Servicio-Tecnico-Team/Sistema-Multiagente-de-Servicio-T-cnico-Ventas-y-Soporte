
import json
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from app.rag.tools import consultar_base_conocimiento
from app.agents.decentralized.state import AgentState
from app.agents.decentralized.policy import (
    ultimo_usuario, es_compatibilidad, es_atencion, handoff, cotizacion_verificada,
    es_inventario, es_marcador,
    normalizar,
    nombre_inventario,
)
from app.agents.decentralized.tools.soporte_tools import transferir_a_soporte
from app.agents.decentralized.tools.ventas_tools import (
    generar_cotizacion,
    transferir_a_tecnico,
    solicitar_inventario,
)


# =========================================================
# CONFIGURACIÓN DEL MODELO
# =========================================================

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    reasoning_effort="low",
    model_kwargs={
        "parallel_tool_calls": False,
        "tool_choice": "auto",
    },
)


# =========================================================
# HERRAMIENTAS
# =========================================================

ventas_tools = [
    solicitar_inventario,
    transferir_a_soporte,
    generar_cotizacion,
    transferir_a_tecnico,
    consultar_base_conocimiento,
]

ventas_llm = llm.bind_tools(ventas_tools)


# =========================================================
# VALIDACIÓN DEL INVENTARIO
# =========================================================

def validar_inventario(state: AgentState):
    """
    Valida los resultados de inventario antes de
    utilizarlos en una cotización.

    Devuelve datos verificados y problemas detectados.
    """

    resultados = state.get("inventory_results", [])
    errores = []

    # Conservar la última ejecución por identificador.
    consultas = {}

    for resultado in resultados:
        identificador = resultado.get("tool_call_id")

        if not identificador:
            errores.append("Consulta sin identificador.")
            continue

        consultas[identificador] = resultado

    inventario = []

    for resultado in consultas.values():
        try:
            nombre = resultado["name"]
            cantidad = resultado["quantity"]
            stock = resultado["stock"]
            precio = Decimal(str(resultado["unit_price"]))
            disponible = resultado["available"]

            if not isinstance(nombre, str) or not nombre.strip():
                raise ValueError("Nombre inválido")

            if type(cantidad) is not int or cantidad <= 0:
                raise ValueError("Cantidad inválida")

            if type(stock) is not int or stock < 0:
                raise ValueError("Stock inválido")

            if not precio.is_finite() or precio < 0:
                raise ValueError("Precio inválido")

            if type(disponible) is not bool:
                raise ValueError("Disponibilidad inválida")

            if disponible != (stock >= cantidad):
                raise ValueError("Disponibilidad inconsistente")

            inventario.append({
                "encontrado": resultado.get("found", True),
                "nombre": nombre,
                "cantidad": cantidad,
                "stock": stock,
                "precio_unitario": str(precio),
                "disponible": disponible,
                "subtotal": (
                    str(precio * cantidad)
                     if disponible
                     else None
                 ),
            })

        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ):
            errores.append("Resultado de inventario inválido.")

    return inventario, errores


# =========================================================
# PROMPT DEL AGENTE
# =========================================================

SYSTEM_PROMPT = """
Eres el agente de Ventas de un sistema multiagente
de servicio técnico, ventas y soporte.

RESPONSABILIDADES:
- Atender consultas comerciales.
- Preparar cotizaciones preliminares.
- Utilizar los resultados verificados de Almacén.
- No inventar precios, existencias ni diagnósticos.

REGLAS:
- Si existe un diagnóstico previo, no lo repitas.
- Los precios de repuestos provienen exclusivamente
  del inventario validado de PostgreSQL.
- No inventes repuestos, cantidades ni precios.
- Si faltan datos del inventario, no calcules
  una cotización total de reparación.
- Si hay un error de inventario, informa que
  no es posible confirmar la cotización.
- Si un repuesto no está disponible, informa
  la falta de stock y no lo ofrezcas como disponible.
- Los precios de servicios de generar_cotizacion
  son estimaciones simuladas, no tarifas verificadas.
- No presentes estimaciones como precios definitivos.
- No sumes importes ni modifiques subtotales
  por tu cuenta.
- No repitas herramientas ya ejecutadas.
- Si se necesita diagnóstico, transfiere a Técnico.
- Si la nueva pregunta es sobre un ticket, atención general o
  revisión presencial, utiliza transferir_a_soporte.
- No puedes reservar citas ni confirmar que se registró una visita.

RAG:
- Consulta la base de conocimiento solo cuando
  necesites información documental.
- Realiza como máximo una consulta RAG
  por solicitud.
- No utilices RAG para inventar precios.

La cotización es preliminar y requiere
confirmación explícita del cliente.
"""


# =========================================================
# CONTEXTO DEL INVENTARIO
# =========================================================

def construir_contexto_inventario(state: AgentState):
    """
    Convierte los datos validados del inventario
    en información contextual para Ventas.
    """

    inventario, errores = validar_inventario(state)

    errores_estado = [
        error for error in state.get("errors", [])
        if "inventario" in error.lower()
    ]

    errores.extend(errores_estado)

    if errores:
        return HumanMessage(
            content=(
                "INVENTARIO: ERROR DE VALIDACIÓN O CONSULTA.\n"
                "No confirmes precios ni disponibilidad.\n"
                "No generes una cotización total.\n"
                + "\n".join(errores)
            )
        )

    if not inventario:
        return HumanMessage(
            content=(
                "INVENTARIO: No existen resultados verificados.\n"
                "No inventes precios de repuestos.\n"
                "Si la solicitud requiere repuestos, "
                "no generes una cotización total."
            )
        )

    return HumanMessage(
        content=(
            "INVENTARIO VALIDADO DE ALMACÉN:\n"
            + json.dumps(
                inventario,
                ensure_ascii=False,
            )
            + "\nEstos son los únicos datos de repuestos "
              "que puedes utilizar. Los subtotales "
              "ya están calculados."
        )
    )


# =========================================================
# CONSTRUCCIÓN DEL CONTEXTO
# =========================================================

def construir_contexto_ventas(state: AgentState):
    """
    Conserva mensajes del usuario, diagnósticos
    técnicos y herramientas de Ventas.
    """

    contexto = []
    messages = state["messages"]

    nombres_tools = {
        "transferir_a_soporte",
        "generar_cotizacion",
        "transferir_a_tecnico",
        "consultar_base_conocimiento",
    }

    llamadas_ventas = set()

    for mensaje in messages:
        if isinstance(mensaje, AIMessage):
            for llamada in mensaje.tool_calls:
                if llamada["name"] in nombres_tools:
                    llamadas_ventas.add(llamada["id"])

    for mensaje in messages:

        if isinstance(mensaje, HumanMessage):
            contexto.append(mensaje)

        elif isinstance(mensaje, AIMessage):
            llamadas = mensaje.tool_calls

            if not llamadas:
                contexto.append(mensaje)
                continue

            if llamadas and all(
                llamada["id"] in llamadas_ventas
                for llamada in llamadas
            ):
                contexto.append(mensaje)

        elif isinstance(mensaje, ToolMessage):

            if mensaje.tool_call_id in llamadas_ventas:
                contexto.append(mensaje)

            elif mensaje.name == "diagnosticar_problema":
                contexto.append(
                    HumanMessage(
                        content=(
                            "Diagnóstico técnico previo:\n"
                            f"{mensaje.content}"
                        )
                    )
                )


    return contexto


# =========================================================
# NODO DEL AGENTE VENTAS
# =========================================================

def ventas_node(state: AgentState):
    """
    Procesa solicitudes comerciales utilizando
    el contexto del inventario validado.
    """

    user = ultimo_usuario(state)
    if es_marcador(user):
        return {"current_agent": "ventas", "messages": [AIMessage(content="Sustituye el texto entre corchetes por el nombre real del repuesto. No puedo consultar un marcador de ejemplo.")]}
    if es_compatibilidad(user):
        return handoff("ventas", "transferir_a_tecnico", motivo="Verificar compatibilidad con evidencia técnica")
    if es_atencion(user):
        return handoff("ventas", "transferir_a_soporte", motivo="Orientación de atención presencial")
    reference = nombre_inventario(user)
    previous_names = [p.get("name", "") for p in state.get("required_parts", [])]
    previous_names.extend(r.get("requested_name", "") for r in state.get("inventory_results", []))
    corrected_reference = reference is not None and not any(
        normalizar(reference).replace(" ", "") == normalizar(name).replace(" ", "")
        for name in previous_names
    )
    if (es_inventario(user) or corrected_reference) and not any(
        isinstance(m, ToolMessage) and m.name == "consultar_inventario"
        for m in state["messages"][state.get("turn_start_index", 0):]
    ):
        return handoff("ventas", "solicitar_inventario", consulta=user)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *construir_contexto_ventas(state),
        construir_contexto_inventario(state),
    ]

    try:
        inventory, problems = validar_inventario(state)
        problems.extend(e for e in state.get("errors", []) if "inventario" in e.lower())
        if inventory or problems or state.get("quote_scope") or state.get("inventory_pending"):
            quote, reply = cotizacion_verificada(inventory, problems, state.get("inventory_pending", False), state.get("quote_scope"))
            if "instalacion" in normalizar(user) and any(w in normalizar(user) for w in ("incluye", "incluido", "solo", "importe")):
                if any(p["subtotal"] is not None for p in quote["parts"]):
                    reply = "El subtotal mostrado corresponde solo a los repuestos disponibles. No incluye instalación ni mano de obra; su tarifa sigue pendiente de validación."
                else:
                    reply = "Todavía no hay un importe de repuestos disponibles confirmado. La tarifa de instalación y mano de obra también está pendiente de validación."
            return {"current_agent": "ventas", "quote": quote, "messages": [AIMessage(content=reply)]}
        response = ventas_llm.invoke(messages)

        if not response.tool_calls:
            quote, reply = cotizacion_verificada([], [])
            return {"current_agent": "ventas", "quote": quote, "messages": [AIMessage(content=reply)]}

        return {
            "messages": [response],
            "current_agent": "ventas",
        }

    except Exception as e:
        error = (
            f"Error en el agente Ventas: "
            f"{type(e).__name__}"
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        "No fue posible procesar la "
                        "cotización en este momento. "
                        "Inténtalo nuevamente más tarde."
                    )
                )
            ],
            "current_agent": "ventas",
            "errors": state.get("errors", []) + [error],
        }

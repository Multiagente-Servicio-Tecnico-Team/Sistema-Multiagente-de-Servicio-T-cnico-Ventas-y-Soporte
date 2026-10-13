"""Reglas locales para datos comerciales y rutas; sin clientes ni servicios."""
import re
import unicodedata
from decimal import Decimal
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage


def normalizar(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def ultimo_usuario(state):
    return next((m.content for m in reversed(state["messages"])
                 if isinstance(m, HumanMessage) and isinstance(m.content, str)), "")


def es_compatibilidad(text):
    text = normalizar(text)
    return any(word in text for word in ("compatib", "sirve para mi", "funciona con mi"))


def triaje_soporte(state):
    """Clasificación conversacional conservadora; nunca confirma una causa."""
    text = normalizar(ultimo_usuario(state))
    if re.search(r"\b(que es|que significa|como funciona)\b", text):
        return None
    # Una respuesta breve puede completar una pregunta previa de Soporte.
    # No recuperar una falla antigua ante una solicitud nueva explícita.
    if len(text.split()) <= 6 and not re.search(r"\b(ticket|horario|precio|stock|presencial)\b", text):
        messages = state.get("messages", [])
        previous = next((m for m in reversed(messages[:-1]) if isinstance(m, AIMessage)), None)
        if previous and isinstance(previous.content, str) and "?" in previous.content:
            humans = [m.content for m in messages if isinstance(m, HumanMessage) and isinstance(m.content, str)]
            if len(humans) >= 2 and any(w in normalizar(previous.content) for w in ("aplicacion", "sistema operativo", "mensaje de error")):
                text = normalizar(humans[-2]) + ". " + text
    hardware = software = False
    clauses = re.split(r"[.!?;,\n]|\b(?:pero|aunque|y)\b", text)
    for clause in clauses:
        if re.search(r"\b(quizas|podria|hipoteticamente|si|creo)\b", clause):
            continue
        # "no enciende" describe una falla; "no quiero cambiar" niega una petición.
        negation_text = re.sub(r"\bno (enciende|arranca|abre|funciona)\b", "falla", clause)
        if re.search(r"\b(no|nunca|tampoco|sin|descarto)\b", negation_text):
            continue
        hardware |= bool(re.search(r"\b(no enciende|sale humo|olor a quemado|bateria (?:esta )?hinchada)\b", clause)
                         or re.search(r"\b(reemplazar|cambiar|falla|averiado|roto)\b.*\b(ssd|ram|fuente|pantalla|bateria|componente)\b", clause))
        software |= bool(re.search(r"\b(aplicacion|programa|editor|navegador)\b.*\b(se cierra|falla|error|no abre)\b", clause)
                         or re.search(r"\b(instalar|actualizar|configurar|configuracion)\b.*\b(windows|linux|ubuntu|macos|controlador|controladores|driver|drivers|aplicacion|programa)\b", clause)
                         or re.search(r"\b(controlador|driver)\b.*\b(error|falla)\b", clause))
    if hardware:
        return "tecnico"
    if software:
        return "software"
    if re.search(r"\b(lento|lentitud|pantalla azul|no enciende|sistema operativo|windows|aplicacion|controlador|driver|humo|ram|ssd)\b", text):
        return "aclarar"
    return None


def es_revision_comercial(text):
    text = normalizar(text)
    return (any(w in text for w in ("revision", "diagnostico"))
            and any(w in text for w in ("cuanto", "precio", "costo", "cuesta", "cotiza")))


def transferencia_sin_progreso(state, origin, destination):
    """Consulta el mismo token de auditoría sin modificar registros ni límites."""
    from app.agents.decentralized.handoffs import progress_token
    token = progress_token(state)
    return any(record.get("origen") == origin and record.get("destino") == destination
               and record.get("request_revision") == state.get("request_revision")
               and record.get("progress_token") == token
               for record in state.get("handoff_records", []))


def peligro_fisico_reportado(text):
    """Indicios de peligro afirmados; una negación no demuestra peligro."""
    return any(re.search(r"\b(sale humo|olor a quemado|bateria (?:esta )?hinchada)\b", clause)
               and not re.search(r"\b(no|nunca|sin|tampoco|quizas|podria|si|creo)\b", clause)
               for clause in re.split(r"[.!?;,\n]|\b(?:pero|aunque|y)\b", normalizar(text)))


def es_atencion(text):
    return bool(re.search(r"\b(citas?|presencial|horarios?|direccion|contacto|contactar)\b", normalizar(text)))


def no_puede_probar(text):
    text = normalizar(text)
    return any(w in text for w in ("no se hacer", "no se conectar", "no sabria", "ni idea", "no puedo hacer", "no se realizar"))


def es_inventario(text):
    text = normalizar(text)
    return any(w in text for w in ("stock", "dispon", "existencias", "que ssd tienes"))


def es_marcador(text):
    text = normalizar(text)
    return "[" in text or "]" in text or "nombre exacto del" in text


def nombre_inventario(text):
    """Solo extrae una referencia SSD explícita; nunca completa capacidad/interfaz."""
    if es_marcador(text):
        return None
    match = re.search(r"\bssd\s*\d+\s*(?:gb|tb)(?:\s+(?:nvme|sata|m\.?2))?", text, re.I)
    return match[0].strip() if match else None


def handoff(agent, tool_name, **args):
    return {"current_agent": agent, "messages": [AIMessage(content="", tool_calls=[
        {"name": tool_name, "args": args, "id": f"handoff-{uuid4().hex}"}
    ])]}


def repuesto_confirmado(state, name):
    """Exige identificación específica aportada por el usuario, no por el modelo."""
    if not isinstance(name, str):
        return False
    normalized = normalizar(name).strip()
    if normalized in {"ssd", "disco", "disco ssd", "ram", "bateria", "pantalla", "fuente", "cargador"}:
        return False
    compact = re.sub(r"\W+", "", normalized)
    return bool(compact) and any(
        compact in re.sub(r"\W+", "", normalizar(m.content))
        for m in state["messages"] if isinstance(m, HumanMessage) and isinstance(m.content, str)
    )


ATENCION_NO_CONFIGURADA = (
    "No puedo reservar citas, registrar visitas ni confirmar que alguien te contactará desde este chat. "
    "No tengo canales, dirección ni horarios de atención verificados para indicarte cómo solicitar una visita. "
    "La revisión presencial es una recomendación; todavía no hay una reserva ni una solicitud registrada."
)


def cotizacion_verificada(inventory, errors, pending=False, scope=None):
    """Mano de obra sin tarifa oficial: nunca producir total ni importe inventado."""
    quote = {"currency": "PEN", "status": "incomplete", "parts": [],
             "labor_total": None, "total": None, "known_parts_subtotal": None}
    if scope == "solo_servicio":
        return quote, "La tarifa de revisión o mano de obra está pendiente de validación. No puedo confirmar un precio. No incluye repuestos."
    if errors or pending:
        return quote, "No puedo confirmar disponibilidad ni precios: el inventario sigue pendiente o tiene errores."
    if not inventory:
        return quote, "No hay resultados de inventario verificados. La tarifa de mano de obra está pendiente; no puedo confirmar un total."
    lines = ["Cotización preliminar de repuestos (PEN):"]
    subtotal = Decimal("0.00")
    seen = set()
    for item in inventory:
        key = (item["nombre"], item["cantidad"])
        if key in seen:
            continue
        seen.add(key)
        if not item.get("encontrado", True):
            lines.append(f"{item['nombre']}: no se encontró una referencia única coincidente. Confirma la capacidad, interfaz y nombre; no sustituiré el repuesto por otro.")
            continue
        price = Decimal(item["precio_unitario"]).quantize(Decimal("0.01"))
        amount = (price * item["cantidad"]).quantize(Decimal("0.01")) if item["disponible"] else None
        quote["parts"].append({"name": item["nombre"], "quantity": item["cantidad"],
                               "stock": item["stock"], "unit_price": str(price),
                               "available": item["disponible"], "subtotal": str(amount) if amount is not None else None})
        lines.append(f"{item['nombre']}: cantidad solicitada {item['cantidad']}; stock {item['stock']}; "
                     f"precio unitario S/ {price}; " + (f"subtotal S/ {amount}." if amount is not None else "stock insuficiente."))
        if amount is not None:
            subtotal += amount
    if quote["parts"]:
        quote["known_parts_subtotal"] = str(subtotal)
        lines.append(f"Subtotal de repuestos disponibles: S/ {subtotal}.")
    lines.extend([
                  "Instalación y mano de obra no incluidas: tarifa pendiente de validación. No hay un total final.",
                  "Disponibilidad no confirma compatibilidad. No se ha reservado stock ni confirmado una compra."])
    return quote, "\n".join(lines)


def software_comercial_elegible(state):
    """Elegibilidad conversacional; no certifica diagnóstico, precio ni ejecución."""
    assessment = state.get("technical_assessment", {})
    if not isinstance(assessment, dict):
        return False
    user = normalizar(ultimo_usuario(state))
    diagnosis = assessment.get("software_diagnosis")
    revision = state.get("request_revision")
    # TechnicalAssessment no contiene revisión ni estado de resolución por área.
    # Una revisión global no fecha el diagnóstico: exigir reconfirmación actual
    # de su texto exacto y no interpretar un registro Hardware como ya resuelto.
    clauses = re.split(r"[.!?;\n,]|\b(?:pero|aunque|sin embargo|y)\b", user)
    def affirmative(clause):
        return not re.search(r"\b(no|nunca|jamas|sin|tampoco|descartado|descarto|quizas|podria|si)\b",
                             clause.replace("sin repuestos", ""))
    return (
        isinstance(diagnosis, str) and bool(diagnosis.strip())
        and type(revision) is int and revision >= 0
        and any(re.search(r"\bconfirmo\b", clause)
                and normalizar(diagnosis.strip()) in clause and affirmative(clause)
                for clause in clauses)
        and not assessment.get("uncertainties")
        and not assessment.get("compatibility_pending")
        and not state.get("required_parts")
        and not state.get("requested_items")
        and not assessment.get("hardware_diagnosis")
        and any(re.search(r"\b(precio|cotiza|cotizar|costo|cuanto)\b", clause)
                and affirmative(clause) for clause in clauses)
        and any(any(term in clause for term in ("sin repuestos", "solo servicio", "solo diagnostico"))
                and affirmative(clause) for clause in clauses)
    )


def inventario_vigente(state, required=None):
    """Reutiliza únicamente resultados de la revisión y requerimiento actuales."""
    revision = state.get("request_revision", 0)
    if (type(revision) is not int or revision < 0
            or type(state.get("inventory_revision")) is not int
            or state["inventory_revision"] != revision):
        return []
    required = state.get("required_parts", []) if required is None else required
    return [item for item in state.get("inventory_results", [])
            if any(item.get("requested_name") == part.get("name")
                   and item.get("quantity") == part.get("quantity") for part in required)]


def preparar_inventario(state, required):
    """Cada requerimiento comercial retorna a Ventas; conserva coincidencias vigentes."""
    revision = state.get("request_revision", 0)
    if type(revision) is not int or revision < 0:
        raise ValueError("Revisión de inventario inválida")
    results = inventario_vigente(state, required)
    complete = bool(required) and all(any(item.get("requested_name") == part["name"]
                                         and item.get("quantity") == part["quantity"]
                                         for item in results) for part in required)
    return {"request_revision": revision, "required_parts": required,
            "inventory_results": results, "inventory_revision": revision if results else None,
            "inventory_pending": not complete, "inventory_requested_by": "ventas"}

from app.agents.jerarquico.agents.faq import MarkdownFaqRetriever


def test_faq_retriever_selects_topic_for_natural_questions():
    retriever = MarkdownFaqRetriever()
    cases = {
        "tengo una consulta que funciones puedes realizar": "Servicios disponibles",
        "donde queda la tienda": "Ubicación de la tienda",
        "cual es el horario de atencion": "Horario de atención",
        "que medios de pago aceptan": "Pagos",
        "como consulto mi garantia": "Garantía",
        "puedo recoger mi equipo presencialmente": "Retiro y envío",
        "tienen RAM disponible": "Compras y disponibilidad",
    }

    for question, expected_heading in cases.items():
        context = retriever.retrieve(question, limit=1)
        assert expected_heading in context, question


def test_faq_content_does_not_contain_a_simulated_store_address_or_hours():
    retriever = MarkdownFaqRetriever()
    location = retriever.retrieve("donde esta el local", limit=1).casefold()
    hours = retriever.retrieve("cuando abren", limit=1).casefold()

    assert "no hay una dirección física confirmada" in location
    assert "circuitos 404" not in location
    assert "no hay un horario de atención confirmado" in hours
    assert "09:00" not in hours

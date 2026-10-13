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


def test_faq_retriever_provides_store_address_and_opening_hours():
    retriever = MarkdownFaqRetriever()
    location = retriever.retrieve("donde esta el local", limit=1).casefold()
    hours = retriever.retrieve("cuando abren", limit=1).casefold()

    assert "sí, contamos con tienda física" in location
    assert "av. los talleres 450, san borja, lima, perú" in location
    assert "lunes a viernes de 09:00 a 18:00" in hours
    assert "sábados de 09:00 a 13:00" in hours

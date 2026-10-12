from langchain_core.tools import tool

from app.rag.retriever import buscar_conocimiento


@tool
def consultar_base_conocimiento(consulta: str) -> str:
    """Consulta la base de conocimiento del servicio técnico."""

    documentos = buscar_conocimiento(
        consulta=consulta,
        k=2,
    )

    if not documentos:
        return "No se encontró información relevante."

    resultados = []

    for documento in documentos:
        fuente = documento.metadata.get("source", "desconocida")

        resultados.append(
            f"Fuente: {fuente}\n"
            f"{documento.page_content}"
        )

    return "\n\n".join(resultados)


if __name__ == "__main__":
    resultado = consultar_base_conocimiento.invoke(
        {
            "consulta": "¿Qué revisar si una computadora no enciende?"
        }
    )

    print(resultado)
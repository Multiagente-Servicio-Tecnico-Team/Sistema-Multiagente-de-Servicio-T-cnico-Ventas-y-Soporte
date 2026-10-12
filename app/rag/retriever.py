from pathlib import Path
from langchain_chroma import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings


BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BASE_DIR / "data" / "chroma"

COLLECTION_NAME = "servicio_tecnico"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def crear_embeddings():
    """Inicializa el mismo modelo usado durante la ingesta."""
    return FastEmbedEmbeddings(
        model_name=EMBEDDING_MODEL
    )


def obtener_vectorstore():
    """Carga la base vectorial almacenada en Chroma."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=crear_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def buscar_conocimiento(consulta: str, k: int = 3):
    """Busca los fragmentos más relacionados con la consulta."""
    vectorstore = obtener_vectorstore()

    return vectorstore.similarity_search(
        consulta,
        k=k,
    )


if __name__ == "__main__":
    resultados = buscar_conocimiento(
        "¿Qué debo revisar si una computadora no enciende?"
    )

    for i, documento in enumerate(resultados, start=1):
        print(f"\n--- Resultado {i} ---")
        print(f"Fuente: {documento.metadata.get('source')}")
        print(documento.page_content)
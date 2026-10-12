from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
CHROMA_DIR = BASE_DIR / "data" / "chroma"

# Configuración
COLLECTION_NAME = "servicio_tecnico"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

def cargar_documentos():
    """Carga los documentos Markdown de la base de conocimiento."""

    documentos = []

    for archivo in sorted(KNOWLEDGE_DIR.glob("*.md")):
        contenido = archivo.read_text(encoding="utf-8")

        documento = Document(
            page_content=contenido,
            metadata={
                "source": archivo.name,
                "area": archivo.stem,
            },
        )

        documentos.append(documento)

    return documentos


def dividir_documentos(documentos):
    """Divide los documentos en fragmentos para su vectorización."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
    )

    return splitter.split_documents(documentos)


def crear_embeddings():
    """Inicializa el modelo local de embeddings mediante FastEmbed."""

    return FastEmbedEmbeddings(
        model_name=EMBEDDING_MODEL
    )


def crear_base_vectorial():
    """Crea la base vectorial Chroma a partir del conocimiento."""

    documentos = cargar_documentos()

    if not documentos:
        raise RuntimeError(
            "No se encontraron documentos en data/knowledge."
        )

    chunks = dividir_documentos(documentos)
    embeddings = crear_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )

    return vectorstore, documentos, chunks


if __name__ == "__main__":
    _, documentos, chunks = crear_base_vectorial()

    print("Base vectorial creada correctamente.")
    print(f"Documentos procesados: {len(documentos)}")
    print(f"Chunks generados: {len(chunks)}")
    print(f"Ubicación: {CHROMA_DIR}")
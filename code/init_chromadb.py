"""
Indicizza i PDF presenti in materiali_policy/ in una collection ChromaDB
persistente. Come richiesto dalla traccia, ogni PDF (breve) viene indicizzato
come UN UNICO documento, senza chunking a livello di paragrafo.
Idempotente: uso l'id = nome del file come chiave, e upsert invece di add,
cosi' rilanciare lo script sovrascrive senza duplicare la entry.
"""
from pathlib import Path

import chromadb
from pypdf import PdfReader

from embedder_ollama import OllamaBGEEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_PATH = BASE_DIR / "database" / "chroma_store"
PDF_DIR = BASE_DIR / "materiali_policy"


def estrai_testo(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def init_chromadb():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name="policy_greenwheels",
        embedding_function=OllamaBGEEmbeddingFunction(),
    )

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"Nessun PDF trovato in {PDF_DIR}. Copia li' i 3 documenti forniti.")
        return

    for pdf_path in pdf_files:
        testo_completo = estrai_testo(pdf_path)
        # upsert = idempotente: se rilancio lo script con lo stesso id
        # aggiorna il documento invece di duplicarlo
        collection.upsert(
            ids=[pdf_path.stem],
            documents=[testo_completo],
            metadatas=[{"source": pdf_path.name}],
        )
        print(f"Indicizzato: {pdf_path.name} ({len(testo_completo)} caratteri)")

    print(f"Collection 'policy_greenwheels' pronta in {CHROMA_PATH} "
          f"({collection.count()} documenti totali)")


if __name__ == "__main__":
    init_chromadb()

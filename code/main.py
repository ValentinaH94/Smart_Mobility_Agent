"""
Entry point unico del progetto. In VSCode ti basta eseguire questo file
(F5, oppure `python main.py` dal terminale integrato con il venv attivo).

Cosa fa, in ordine:
1. Se mobility.db non esiste ancora -> lo crea e lo popola (init_sqlite).
2. Se la collection ChromaDB e' vuota -> indicizza i PDF in materiali_policy/
   (init_chromadb). Se non trova PDF, avvisa ma non blocca l'esecuzione.
3. Avvia il loop di chat (agent.main()).

E' idempotente: se lanci main.py piu' volte, i passi 1 e 2 vengono saltati
automaticamente perche' i dati esistono gia'.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mobility.db"


def assicura_sqlite():
    if DB_PATH.exists():
        print(f"[main] mobility.db già presente ({DB_PATH}), skip inizializzazione.")
        return
    print("[main] mobility.db non trovato: inizializzo...")
    from init_sqlite import init_db
    init_db()


def assicura_chromadb():
    import chromadb
    from embedder_ollama import OllamaBGEEmbeddingFunction

    chroma_path = BASE_DIR / "database" / "chroma_store"
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(
        name="policy_greenwheels",
        embedding_function=OllamaBGEEmbeddingFunction(),
    )

    if collection.count() > 0:
        print(f"[main] Collection ChromaDB già popolata ({collection.count()} documenti), skip.")
        return

    pdf_dir = BASE_DIR / "materiali_policy"
    if not any(pdf_dir.glob("*.pdf")):
        print(f"[main] ATTENZIONE: nessun PDF trovato in {pdf_dir}. "
              "Copia lì i 3 documenti forniti prima di fare domande di policy.")
        return

    print("[main] Collection ChromaDB vuota: indicizzo i PDF...")
    from init_chromadb import init_chromadb
    init_chromadb()


def main():
    print("=== GreenWheels Smart Mobility Chatbot — avvio ===\n")
    assicura_sqlite()
    assicura_chromadb()
    print()

    from agent import main as avvia_chat
    avvia_chat()


if __name__ == "__main__":
    main()
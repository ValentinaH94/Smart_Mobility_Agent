"""
Funzioni Python "pure" che l'agente LLM potra' invocare tramite tool-use.
Principio guida (vedi teoria.txt, Domanda 2): il modello puo' SOLO proporre
QUALI parametri passare a una funzione con uno schema tipizzato; il calcolo
del costo e la scrittura sul DB avvengono SEMPRE qui, nel codice, mai nel
ragionamento libero del LLM. Questo e' cio' che rende il sistema resistente
a un utente che tenta di manipolare il prezzo via prompt.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from embedder_ollama import OllamaBGEEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "mobility.db"
CHROMA_PATH = BASE_DIR / "database" / "chroma_store"
RECEIPT_PATH = BASE_DIR / "ricevuta_noleggio.json"

_chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
_collection = _chroma_client.get_or_create_collection(
    name="policy_greenwheels",
    embedding_function=OllamaBGEEmbeddingFunction(),
)


# ---------------------------------------------------------------------------
# TOOL 1 - Policy Agent: ricerca semantica su ChromaDB
# ---------------------------------------------------------------------------
def query_policy_kb(domanda: str, k: int = 3) -> dict:
    """Cerca nella base di conoscenza (policy, listino, regolamento) i
    passaggi piu' pertinenti rispetto alla domanda dell'utente."""
    risultati = _collection.query(query_texts=[domanda], n_results=k)

    documenti = risultati["documents"][0]
    metadati = risultati["metadatas"][0]
    distanze = risultati["distances"][0]

    passaggi = [
        {"source": meta.get("source"), "testo": doc, "distanza": round(dist, 4)}
        for doc, meta, dist in zip(documenti, metadati, distanze)
    ]
    # Espongo esplicitamente le fonti (source) recuperate: serve al modello
    # per non mescolare informazioni contraddittorie tra i 3 documenti
    # (che si sovrappongono parzialmente, come segnalato nella traccia).
    return {"passaggi_trovati": passaggi}


# ---------------------------------------------------------------------------
# TOOL 2 - Booking Agent: verifica disponibilita' (sola lettura)
# ---------------------------------------------------------------------------
def check_availability(veicolo_id: int) -> dict:
    """Verifica se un veicolo e' attualmente disponibile per la prenotazione."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT tipo, tariffa_oraria, disponibile FROM veicoli WHERE id = ?",
        (veicolo_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return {"trovato": False, "disponibile": False,
                "messaggio": f"Nessun veicolo con id {veicolo_id}."}

    tipo, tariffa, disponibile = row
    return {
        "trovato": True,
        "disponibile": bool(disponibile),
        "tipo": tipo,
        "tariffa_oraria": tariffa,
    }


# ---------------------------------------------------------------------------
# TOOL 3 - Booking Agent: transazione atomica + ricevuta
# ---------------------------------------------------------------------------
def create_booking(utente_id: int, veicolo_id: int, ore: float) -> dict:
    """Crea una prenotazione in modo atomico: verifica di nuovo la
    disponibilita' DENTRO la transazione (evita race condition / doppie
    prenotazioni), calcola il costo lato codice e aggiorna lo stato del
    veicolo. Se qualcosa fallisce, esegue il rollback: nessuna scrittura
    parziale, nessun file JSON generato."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Vincoli espliciti sui parametri, oltre al tipo dichiarato nello schema
    # del tool: un tipo (int/float) da solo non basta a garantire dati
    # sensati, va validato anche il range/dominio di validita'.
    if ore <= 0:
        conn.close()
        return {"successo": False, "errore": "Il numero di ore deve essere maggiore di zero."}
    if utente_id <= 0 or veicolo_id <= 0:
        conn.close()
        return {"successo": False, "errore": "utente_id e veicolo_id devono essere interi positivi."}

    try:
        # BEGIN IMMEDIATE blocca subito il DB in scrittura, cosi' due
        # richieste concorrenti sullo stesso veicolo non possono passare
        # entrambe il controllo di disponibilita'.
        cur.execute("BEGIN IMMEDIATE")

        cur.execute(
            "SELECT nome FROM utenti WHERE id = ?", (utente_id,)
        )
        utente_row = cur.fetchone()
        if utente_row is None:
            conn.rollback()
            return {"successo": False, "errore": f"Utente {utente_id} non trovato."}

        cur.execute(
            "SELECT tipo, tariffa_oraria, disponibile FROM veicoli WHERE id = ?",
            (veicolo_id,),
        )
        veicolo_row = cur.fetchone()
        if veicolo_row is None:
            conn.rollback()
            return {"successo": False, "errore": f"Veicolo {veicolo_id} non trovato."}

        tipo, tariffa_oraria, disponibile = veicolo_row
        if not disponibile:
            conn.rollback()
            return {
                "successo": False,
                "errore": f"Il veicolo '{tipo}' (id {veicolo_id}) non e' disponibile.",
            }

        # Unico punto in cui il costo viene calcolato: mai delegato al LLM.
        costo_totale = round(tariffa_oraria * ore, 2)

        cur.execute(
            "INSERT INTO prenotazioni (utente_id, veicolo_id, ore, costo_totale) "
            "VALUES (?, ?, ?, ?)",
            (utente_id, veicolo_id, ore, costo_totale),
        )
        cur.execute(
            "UPDATE veicoli SET disponibile = 0 WHERE id = ?", (veicolo_id,)
        )

        conn.commit()

    except Exception as exc:
        conn.rollback()
        return {"successo": False, "errore": f"Errore imprevisto: {exc}"}
    finally:
        conn.close()

    ricevuta = {
        "cliente": {"id": utente_id, "nome": utente_row[0]},
        "veicolo": {"id": veicolo_id, "tipo": tipo},
        "ore_noleggio": ore,
        "tariffa_oraria": tariffa_oraria,
        "costo_totale": costo_totale,
        "note_policy": (
            "Franchigia ed eventuali penali (fuori zona, ritardo riconsegna) "
            "sono regolate dalla policy assicurativa GreenWheels."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    RECEIPT_PATH.write_text(
        json.dumps(ricevuta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {"successo": True, "ricevuta": ricevuta, "file": str(RECEIPT_PATH)}


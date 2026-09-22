"""
Inizializza mobility.db: crea le tabelle (se non esistono) e inserisce
dati di test solo se le tabelle sono vuote -> lo script e' idempotente,
puo' essere rilanciato senza duplicare nulla.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "mobility.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Le foreign key in SQLite non sono attive di default: vanno abilitate
    # esplicitamente per ogni connessione.
    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS veicoli (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            tariffa_oraria REAL NOT NULL,
            disponibile INTEGER NOT NULL DEFAULT 1  -- 1 = disponibile, 0 = prenotato
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prenotazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utente_id INTEGER NOT NULL,
            veicolo_id INTEGER NOT NULL,
            ore REAL NOT NULL,
            costo_totale REAL NOT NULL,
            FOREIGN KEY (utente_id) REFERENCES utenti(id),
            FOREIGN KEY (veicolo_id) REFERENCES veicoli(id)
        )
    """)

    # Popolamento idempotente: inserisco i dati di test solo se le tabelle
    # sono vuote, cosi' rilanciare lo script non crea duplicati.
    cur.execute("SELECT COUNT(*) FROM utenti")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO utenti (nome, email) VALUES (?, ?)",
            [
                ("Mario Rossi", "mario.rossi@example.com"),
                ("Giulia Bianchi", "giulia.bianchi@example.com"),
                ("Luca Verdi", "luca.verdi@example.com"),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM veicoli")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO veicoli (tipo, tariffa_oraria, disponibile) VALUES (?, ?, ?)",
            [
                ("e-bike", 3.0, 1),
                ("monopattino", 2.0, 1),
                ("city car elettrica", 8.5, 1),
                ("SUV elettrico", 15.0, 1),
                ("furgone cargo", 12.0, 1),
            ],
        )

    conn.commit()
    conn.close()
    print(f"Database inizializzato correttamente in: {DB_PATH}")


if __name__ == "__main__":
    init_db()
# GreenWheels — Smart Mobility Agentic Chatbot

Chatbot agentico per un servizio di noleggio veicoli elettrici (e-bike, monopattini, city car, SUV elettrici, furgoni cargo), capace di rispondere a domande su policy/tariffe recuperando informazioni da documenti aziendali (RAG) e di gestire prenotazioni reali in modo transazionale e sicuro su database relazionale.

## Cosa fa

- **Risponde a domande su policy, tariffe, assicurazione e regolamento** cercando semanticamente nei documenti aziendali (PDF), non a memoria — così le risposte sono sempre ancorate a una fonte reale.
- **Gestisce prenotazioni end-to-end**: verifica disponibilità del veicolo, chiede conferma esplicita all'utente, esegue la transazione sul database e genera automaticamente una ricevuta in JSON.
- **Instrada ogni richiesta al sotto-agente giusto** (informativo o transazionale) tramite *tool-use nativo* del modello — nessuna logica if/elif su parole chiave: è il modello a decidere leggendo ruolo e strumenti disponibili di ciascun agente.
- **Non delega mai al modello i calcoli critici**: il costo di una prenotazione è sempre calcolato dal codice, mai generato dal LLM — anche se un utente tenta di manipolarlo via prompt, non c'è alcun canale attraverso cui l'informazione possa raggiungere il database.

## Architettura

```
                    ┌──────────────────────┐
   Utente  ───────► │   Crew Manager       │
                    │ (routing via tool-use│
                    │  nativo del modello) │
                    └─────────┬────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
     ┌─────────────────┐            ┌──────────────────────┐
     │  Policy Agent     │            │   Booking Agent       │
     │  (RAG)             │            │   (transazionale)      │
     └────────┬──────────┘            └──────────┬────────────┘
              │                                    │
              ▼                                    ▼
     ┌─────────────────┐            ┌──────────────────────┐
     │  ChromaDB          │            │   SQLite               │
     │  (embedding bge-m3  │            │   (transazioni ACID,    │
     │   via Ollama)        │            │   commit/rollback)      │
     └─────────────────┘            └──────────────────────┘
```

**Perché due database diversi?** Le policy sono testo non strutturato e semanticamente ambiguo → serve il dense retrieval (embedding + similarità coseno) di un vector database. Le prenotazioni sono dati relazionali che richiedono garanzie ACID (atomicità, isolamento) → serve un database relazionale con transazioni vere, non un vector store.

## Stack tecnico

| Componente | Tecnologia |
|---|---|
| Orchestrazione agenti | [CrewAI](https://www.crewai.com/) (`Process.hierarchical`) |
| LLM | Modelli locali via [Ollama](https://ollama.com/) (es. qwen2.5) |
| Embedding | bge-m3 via Ollama |
| Vector DB | ChromaDB |
| Database relazionale | SQLite (transazioni `BEGIN IMMEDIATE` + commit/rollback) |
| Linguaggio | Python 3.12 |

## Struttura del repository

```
Smart_Mobility_Agent/
├── code/                    # tutto il codice sorgente
│   ├── main.py               # entry point
│   ├── agent.py               # agenti CrewAI + orchestrazione
│   ├── crewai_tools_greenwheels.py
│   ├── tools.py                # logica di business (RAG, transazioni)
│   ├── embedder_ollama.py
│   ├── init_sqlite.py
│   └── init_chromadb.py
├── database/                # SQLite + collection ChromaDB
└── materiali_policy/         # documenti aziendali indicizzati (PDF)
```

## Avvio rapido

```bash
# 1. Ambiente
python -m venv venv
venv\Scripts\activate        # Windows — su macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# 2. Modelli Ollama
ollama pull bge-m3
ollama pull qwen2.5
ollama serve

# 3. Avvio (inizializza i DB al primo avvio, poi apre la chat)
cd code
python main.py
```

## Punti di design degni di nota

- **Idempotenza**: ogni script di inizializzazione (`init_sqlite.py`, `init_chromadb.py`) può essere rilanciato senza duplicare dati.
- **Race condition**: la disponibilità di un veicolo viene verificata di nuovo *dentro* la transazione stessa (non solo a livello di conversazione), evitando che due richieste concorrenti prenotino lo stesso veicolo.
- **Validazione dei parametri**: i tool esposti al modello dichiarano vincoli espliciti (es. ore > 0, ID positivi), non solo il tipo — riduce la superficie di errore anche in caso di input inatteso dal modello.

---

*Progetto realizzato come esercitazione su architetture agentiche multi-agente con LLM locali.*

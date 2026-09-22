# GreenWheels Smart Mobility Chatbot — guida rapida

## 1. Ambiente
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## 2. Ollama
```bash
ollama pull bge-m3           # embedding model per ChromaDB
ollama pull qwen2.5          # (o llama3.1) modello di chat con function calling
ollama list                  # verifica che compaiano entrambi
ollama serve                 # assicurati che sia in ascolto su localhost:11434
```

L'agente usa CrewAI (`agent.py`), con `LLM(model="ollama/qwen2.5", base_url="http://localhost:11434")`.
Se cambi modello, aggiorna la stringa `"ollama/<nome_modello>"` sia in `agent.py`
sia nel comando `ollama pull`.

## 3. Materiali
Copia i 3 PDF forniti dalla traccia in `../materiali_policy/`:
- policy_noleggio_assicurazione.pdf
- listino_prezzi_veicoli.pdf
- regolamento_generale_sicurezza.pdf

## 4. Avvio (unico comando)
```bash
python main.py
```
`main.py` controlla automaticamente se `mobility.db` esiste e se la collection
ChromaDB è già popolata: se mancano, li inizializza al volo (chiamando
`init_sqlite.py` / `init_chromadb.py`), poi avvia direttamente la chat.
Puoi comunque lanciare `init_sqlite.py` e `init_chromadb.py` separatamente
se vuoi ricostruirli da zero (sono idempotenti).

## 5. Test suggeriti per conversazione_log.txt
1. Domanda informativa (RAG): "Quanto costa la penale se lascio il mezzo fuori zona?"
2. Prenotazione riuscita: chiedi di prenotare un veicolo disponibile, conferma, verifica che
   venga creato `ricevuta_noleggio.json` nella root del progetto.
3. Prenotazione fallita: richiedi lo stesso veicolo appena prenotato (ora `disponibile = 0`)
   e verifica che il sistema spieghi l'errore senza scrivere nulla sul DB.

Copia l'intera trascrizione del terminale in `conversazione_log.txt`.
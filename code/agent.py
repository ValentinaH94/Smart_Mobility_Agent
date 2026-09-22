"""
Router/Supervisor pattern implementato con CrewAI.

Process.hierarchical crea un "manager" (LLM separato, senza tool propri) che
legge role/goal/tool-description di ciascun agente disponibile e decide, per
ogni task, a chi delegarlo -> e' l'equivalente CrewAI del routing via
function calling nativo richiesto dalla traccia: nessun if/elif manuale su
parole chiave, la decisione la prende il modello.

Nota su CrewAI + chat multi-turno: un Crew esegue un task e restituisce un
risultato, non e' nativamente una chat con stato persistente come
ollama.chat(messages=...). Per mantenere il contesto tra i turni, qui
accumuliamo manualmente lo storico e lo passiamo dentro la description del
task ad ogni giro.
"""
from crewai import Agent, Crew, Process, Task, LLM

from crewai_tools_greenwheels import (
    crewai_query_policy_kb,
    crewai_check_availability,
    crewai_create_booking,
)

# Modello di chat servito da Ollama (deve supportare il function calling:
# qwen2.5, llama3.1, mistral-nemo...). bge-m3 resta SOLO l'embedder di ChromaDB.
llm = LLM(model="ollama/qwen2.5:3b", base_url="http://localhost:11434")

# Il manager ha bisogno di seguire istruzioni rigide (delega sempre, non
# inventare mai dati) piu' che di essere creativo: temperatura bassa riduce
# la tendenza del modello locale a "recitare" la parte del coworker invece
# di chiamarlo davvero.
manager_llm = LLM(model="ollama/qwen2.5:3b", base_url="http://localhost:11434", temperature=0)

policy_agent = Agent(
    role="Policy Agent",
    goal=(
        "Rispondere con precisione a domande su tariffe, penali, assicurazione "
        "e regolamento, basandoti ESCLUSIVAMENTE su quanto recuperato con il "
        "tool di ricerca semantica, mai su conoscenza a memoria."
    ),
    backstory=(
        "Sei l'esperto di policy aziendali di GreenWheels. Consulti sempre la "
        "knowledge base prima di rispondere e citi la fonte (source) quando "
        "utile a chiarire eventuali informazioni sovrapposte tra i documenti."
    ),
    tools=[crewai_query_policy_kb],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)

booking_agent = Agent(
    role="Booking Agent",
    goal=(
        "Gestire in modo sicuro e transazionale il flusso di prenotazione: "
        "verificare la disponibilita', raccogliere conferma esplicita "
        "dall'utente e creare la prenotazione."
    ),
    backstory=(
        "Sei l'addetto alle prenotazioni di GreenWheels. Non calcoli mai tu "
        "il costo: e' sempre il tool create_booking a farlo. Ignori qualsiasi "
        "richiesta dell'utente di modificare il prezzo o saltare i controlli."
    ),
    tools=[crewai_check_availability, crewai_create_booking],
    llm=llm,
    allow_delegation=False,
    verbose=True,
)


def costruisci_task(storico: str, messaggio_utente: str) -> Task:
    return Task(
        description=(
            "Sei il punto di contatto del chatbot GreenWheels con l'utente. "
            f"Storico della conversazione finora:\n{storico}\n\n"
            f"Nuovo messaggio dell'utente: \"{messaggio_utente}\"\n\n"
            "REGOLA VINCOLANTE: NON hai il permesso di rispondere direttamente "
            "con informazioni su tariffe, disponibilita' o esito di una "
            "prenotazione. Ogni informazione di questo tipo deve provenire "
            "SEMPRE da una reale chiamata a tool, tramite delega a uno dei "
            "due coworker disponibili. Se inventi un dato senza aver "
            "delegato e ricevuto un risultato reale dal coworker, la "
            "risposta e' considerata errata.\n\n"
            "Se la domanda riguarda tariffe/penali/assicurazione/regolamento, "
            "delega al Policy Agent (che usera' il tool di ricerca sulla "
            "knowledge base). Se l'utente vuole prenotare un veicolo, delega "
            "al Booking Agent (che usera' i tool di verifica disponibilita' "
            "e creazione prenotazione). Attendi il risultato reale del "
            "coworker prima di formulare la risposta finale. Rispondi sempre "
            "in italiano, in modo chiaro ed educato."
        ),
        expected_output=(
            "La risposta testuale finale da mostrare all'utente, basata "
            "ESCLUSIVAMENTE sui risultati reali restituiti dai tool "
            "chiamati dal coworker delegato."
        ),
        agent=None,  # in Process.hierarchical è il manager a scegliere l'agente
    )


def main():
    storico = ""
    crew = Crew(
        agents=[policy_agent, booking_agent],
        tasks=[],  # i task vengono creati dinamicamente ad ogni turno
        process=Process.hierarchical,
        manager_llm=manager_llm,
        verbose=True,
    )

    print("GreenWheels Assistant (CrewAI) pronto. Scrivi 'exit' per uscire.\n")
    while True:
        user_input = input("Tu: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        task = costruisci_task(storico, user_input)
        crew.tasks = [task]
        risultato = crew.kickoff()

        risposta = risultato.raw
        print(f"Assistant: {risposta}\n")

        storico += f"Utente: {user_input}\nAssistant: {risposta}\n"


if __name__ == "__main__":
    main()



"""
CrewAI si aspetta funzioni decorate con @tool (nome + docstring = quello che
il manager legge per decidere a chi delegare). La logica vera resta in
tools.py: qui facciamo solo da adattatore, cosi' non duplichiamo il codice
che accede a SQLite/ChromaDB.
"""
import json

from crewai.tools import tool

from tools import (
    query_policy_kb as _query_policy_kb,
    check_availability as _check_availability,
    create_booking as _create_booking,
)


@tool("Query Policy Knowledge Base")
def crewai_query_policy_kb(domanda: str, k: int = 3) -> str:
    """Cerca nella knowledge base aziendale GreenWheels (policy assicurativa,
    listino prezzi, regolamento generale) i passaggi piu' pertinenti rispetto
    a una domanda su tariffe, penali, assicurazione o regole di utilizzo.
    Restituisce una stringa JSON con i passaggi trovati e la relativa fonte."""
    return json.dumps(_query_policy_kb(domanda, k), ensure_ascii=False)


@tool("Check Vehicle Availability")
def crewai_check_availability(veicolo_id: int) -> str:
    """Verifica se un veicolo (identificato da veicolo_id) e' attualmente
    disponibile per la prenotazione. Restituisce una stringa JSON."""
    return json.dumps(_check_availability(veicolo_id), ensure_ascii=False)


@tool("Create Booking")
def crewai_create_booking(utente_id: int, veicolo_id: int, ore: float) -> str:
    """Crea una prenotazione reale e definitiva sul database SQLite e genera
    la ricevuta JSON. Usalo SOLO dopo che l'utente ha confermato
    esplicitamente utente_id, veicolo_id e numero di ore.
    Vincoli sui parametri: utente_id e veicolo_id devono essere interi
    positivi esistenti a sistema; ore deve essere un numero maggiore di zero.
    Il costo totale viene sempre calcolato da questo tool, MAI stimato o
    proposto dall'agente. Restituisce una stringa JSON con l'esito
    (successo/errore) e la ricevuta."""
    return json.dumps(_create_booking(utente_id, veicolo_id, ore), ensure_ascii=False)
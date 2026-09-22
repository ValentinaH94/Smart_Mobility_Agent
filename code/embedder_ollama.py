"""
ChromaDB richiede una EmbeddingFunction: un oggetto callable che riceve
una lista di stringhe e restituisce una lista di vettori.
Qui la implementiamo appoggiandoci al servizio Ollama locale (nessuna
chiamata a servizi cloud a pagamento), usando il modello multilingue bge-m3.
"""
import ollama
from chromadb import Documents, EmbeddingFunction, Embeddings


class OllamaBGEEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = "bge-m3"):
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        # ChromaDB puo' chiamare questa funzione sia in fase di indicizzazione
        # (collection.add) sia in fase di query (collection.query): in
        # entrambi i casi 'input' e' una lista di stringhe da trasformare
        # nello stesso spazio vettoriale, cosi' la similarita' coseno tra
        # query e documenti indicizzati e' confrontabile.
        return [
            ollama.embeddings(model=self.model_name, prompt=t)["embedding"]
            for t in input
        ]
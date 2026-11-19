"""Grounded document question answering."""

from app.config import get_settings
from app.llm.ollama_client import OllamaClient
from app.rag.vector_store import EventVectorStore


def answer_from_documents(question: str, store: EventVectorStore | None = None) -> tuple[str, list[dict]]:
    if not question.strip():
        raise ValueError("Enter a question about your uploaded documents.")
    vector_store = store or EventVectorStore()
    matches = vector_store.search(question, limit=4)
    if not matches:
        return "I could not find an answer in the uploaded documents.", []
    context = "\n\n".join(f"[Source: {item['source']}]\n{item['text']}" for item in matches)
    prompt = (
        "Answer the question using only the supplied document excerpts. If they do not contain the answer, "
        "say you could not find it. Cite source filenames in the answer.\n\n"
        f"Excerpts:\n{context[:6000]}\n\nQuestion: {question}\nAnswer:"
    )
    settings = get_settings()
    client = OllamaClient(settings)
    return client.generate(prompt), matches

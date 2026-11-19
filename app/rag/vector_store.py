"""Persistent Chroma collection for uploaded event documents."""

from pathlib import Path
from uuid import uuid4

import chromadb

from app.config import get_settings
from app.rag.embeddings import OllamaEmbeddings


class EventVectorStore:
    def __init__(self, path: str | Path = "data/chroma", embeddings: OllamaEmbeddings | None = None) -> None:
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection("event_documents", metadata={"hnsw:space": "cosine"})
        self.embeddings = embeddings or OllamaEmbeddings()

    def add_document(self, name: str, chunks: list[str]) -> int:
        if not chunks:
            raise ValueError("Document has no text chunks to index.")
        vectors = self.embeddings.embed_documents(chunks)
        ids = [str(uuid4()) for _ in chunks]
        metadatas = [{"source": name, "chunk": index} for index in range(len(chunks))]
        self.collection.add(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
        return len(chunks)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not query.strip():
            raise ValueError("Enter a document question.")
        if not 1 <= limit <= 50:
            raise ValueError("Result limit must be between 1 and 50.")
        count = self.collection.count()
        if count == 0:
            return []
        vectors = self.embeddings.embed_query(query)
        result = self.collection.query(query_embeddings=[vectors], n_results=min(limit, count))
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [{"text": doc, "source": meta.get("source", "unknown"), "distance": dist}
                for doc, meta, dist in zip(documents, metadatas, distances) if doc]

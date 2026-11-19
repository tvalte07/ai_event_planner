from pathlib import Path

from app.rag.chunking import split_text
from app.rag.document_loader import extract_text
from app.rag.retriever import answer_from_documents
from app.rag.vector_store import EventVectorStore


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        lowered = text.casefold()
        return [float("vegetarian" in lowered), float("rain" in lowered), float(len(lowered) % 7)]


def test_sample_pdf_extracts_and_chunks_text():
    text = extract_text(Path("data/uploads/sample_catering_menu.pdf"))
    assert "Vegetarian menu ideas" in text
    chunks = split_text(text, chunk_size=300, overlap=40)
    assert len(chunks) > 1
    assert all(chunks)


def test_chroma_indexes_and_retrieves_chunks(tmp_path):
    store = EventVectorStore(tmp_path / "chroma", embeddings=FakeEmbeddings())
    chunks = ["Vegetarian menu includes paneer and dal.", "Outdoor lawn requires a rain plan."]

    assert store.add_document("menu.pdf", chunks) == 2
    matches = store.search("vegetarian menu", limit=1)

    assert matches[0]["source"] == "menu.pdf"
    assert "Vegetarian" in matches[0]["text"]


def test_empty_store_returns_no_retrievals_without_embedding(tmp_path):
    store = EventVectorStore(tmp_path / "empty", embeddings=FakeEmbeddings())
    assert store.search("anything") == []
    answer, sources = answer_from_documents("anything", store)
    assert "could not find" in answer
    assert sources == []

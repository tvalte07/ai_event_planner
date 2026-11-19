"""Ollama embeddings using the locally installed nomic model."""

from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import get_settings


@dataclass(frozen=True)
class OllamaEmbeddings:
    model: str = ""
    base_url: str = ""
    timeout_seconds: int = 60

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        model = self.model or settings.embedding_model
        url = (self.base_url or settings.ollama_base_url).rstrip("/") + "/api/embed"
        payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
        request = Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama embedding request failed; verify Ollama and model {model}.") from exc
        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise RuntimeError("Ollama returned an unexpected embedding response.")
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

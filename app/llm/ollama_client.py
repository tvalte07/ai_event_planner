"""Minimal Ollama HTTP client using only the Python standard library."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings, get_settings


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns an invalid response."""


class OllamaClient:
    """Small synchronous client suitable for the sequential local MVP."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def list_models(self) -> list[str]:
        """Return locally available model names."""
        payload = self._request_json("/api/tags")
        return [item["name"] for item in payload.get("models", []) if "name" in item]

    def generate(self, prompt: str) -> str:
        """Generate a short response from the configured model."""
        body = json.dumps({
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            # Qwen3 may spend a short output budget in its private thinking
            # phase and return an empty `response`. Disable thinking for the
            # app's concise user-facing generation requests.
            "think": False,
            "options": {"num_ctx": 4096, "num_predict": 512},
        }).encode("utf-8")
        payload = self._request_json("/api/generate", body)
        response = payload.get("response")
        if not isinstance(response, str):
            raise OllamaError("Ollama returned a response in an unexpected format.")
        response = response.strip()
        if not response:
            raise OllamaError("Ollama returned an empty answer. Try again or check the configured model.")
        return response

    def _request_json(self, path: str, body: bytes | None = None) -> dict:
        headers = {"Content-Type": "application/json"} if body is not None else {}
        request = Request(f"{self.settings.ollama_base_url}{path}", data=body, headers=headers)
        try:
            with urlopen(request, timeout=self.settings.ollama_timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.settings.ollama_base_url}. "
                "Check that Ollama is running."
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaError("Ollama returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise OllamaError("Ollama returned an unexpected response format.")
        return result

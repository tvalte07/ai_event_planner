"""Lightweight keyword search over locally stored text documents.

This is a Phase 3 utility, not semantic retrieval. PDF extraction, chunking,
embeddings, and ChromaDB are reserved for the RAG phase.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentMatch:
    file_name: str
    line_number: int
    excerpt: str


def search_event_documents(query: str, directory: str | Path | None = None, max_results: int = 10) -> tuple[DocumentMatch, ...]:
    """Find case-insensitive literal matches in local TXT and Markdown files."""
    query = query.strip()
    if not query:
        raise ValueError("Enter a search query.")
    if not 1 <= max_results <= 100:
        raise ValueError("Maximum results must be between 1 and 100.")
    root = Path(directory) if directory is not None else Path(__file__).resolve().parents[2] / "data" / "uploads"
    if not root.exists():
        return ()
    if not root.is_dir():
        raise ValueError("Document search location must be a directory.")

    matches: list[DocumentMatch] = []
    try:
        paths = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() in {".txt", ".md"})
        for path in paths:
            try:
                for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    if query.casefold() in line.casefold():
                        matches.append(DocumentMatch(path.name, line_number, line.strip()[:500]))
                        if len(matches) >= max_results:
                            return tuple(matches)
            except (OSError, UnicodeError):
                continue
    except OSError as exc:
        raise RuntimeError("Could not search the local document directory.") from exc
    return tuple(matches)

"""Small overlap-aware text chunker."""


def split_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    if chunk_size < 100 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk size must be at least 100 and overlap must be smaller than chunk size.")
    normalized = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks

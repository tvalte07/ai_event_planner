"""Extract text from uploaded PDF and TXT documents."""

from io import BytesIO
from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def extract_text_bytes(name: str, content: bytes) -> str:
    """Extract an uploaded document directly from memory, without temp files."""
    suffix = Path(name).suffix.casefold()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF and TXT documents are supported.")
    if suffix == ".txt":
        try:
            text = content.decode("utf-8")
        except UnicodeError as exc:
            raise RuntimeError(f"Could not decode document {name} as UTF-8 text.") from exc
    else:
        from pypdf import PdfReader

        try:
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not read document {name}.") from exc
    text = text.strip()
    if not text:
        raise ValueError("No extractable text was found in this document.")
    return text


def extract_text(path: str | Path) -> str:
    """Extract text from a local PDF or TXT path."""
    source = Path(path)
    try:
        content = source.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Could not read document {source.name}.") from exc
    return extract_text_bytes(source.name, content)

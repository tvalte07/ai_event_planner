from io import BytesIO
from types import SimpleNamespace
import sys

import pytest

from app.rag.document_loader import extract_text_bytes


def test_uploaded_pdf_is_parsed_from_memory_not_reopened_path(monkeypatch) -> None:
    def fake_pdf_reader(source, strict=False):
        assert isinstance(source, BytesIO)
        assert source.read() == b"fake-pdf-bytes"
        return SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda: "Outdoor lawn has a rain plan.")])

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=fake_pdf_reader))

    assert extract_text_bytes("sample.pdf", b"fake-pdf-bytes") == "Outdoor lawn has a rain plan."


def test_uploaded_text_file_decodes_utf8_without_pdf_dependency() -> None:
    assert extract_text_bytes("notes.txt", "Food menu: vegetarian".encode()) == "Food menu: vegetarian"


def test_uploaded_document_rejects_unknown_types_and_empty_text() -> None:
    with pytest.raises(ValueError, match="Only PDF and TXT"):
        extract_text_bytes("menu.docx", b"content")
    with pytest.raises(ValueError, match="No extractable text"):
        extract_text_bytes("blank.txt", b"  \n")

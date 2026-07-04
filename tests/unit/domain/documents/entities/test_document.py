from datetime import datetime
from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.domain.documents.entities.document_chunk import DocumentChunk


def _doc(status="approved", deleted_at=None):
    now = datetime(2026, 1, 1)
    return Document(uuid4(), "pid", "Título", "conteúdo", "https://n", status, now, now, deleted_at)


def test_approved_document_is_approved():
    assert _doc().is_approved() is True


def test_non_approved_or_deleted_is_not_approved():
    assert _doc(status="pending").is_approved() is False
    assert _doc(deleted_at=datetime(2026, 2, 1)).is_approved() is False


def test_chunk_holds_embedding():
    c = DocumentChunk(uuid4(), uuid4(), 0, "trecho", [0.1, 0.2])
    assert c.ordinal == 0 and c.embedding == [0.1, 0.2]

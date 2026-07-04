from datetime import datetime
from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.mappers.document_mapper import DocumentMapper
from src.domain.documents.mappers.document_chunk_mapper import DocumentChunkMapper


def test_document_to_model_attrs_roundtrip_fields():
    now = datetime(2026, 1, 1)
    doc = Document(uuid4(), "pid", "T", "C", "https://n", "approved", now, now, None)
    attrs = DocumentMapper.to_model_attrs(doc)
    assert attrs["notion_page_id"] == "pid"
    assert attrs["status"] == "approved"
    assert "created_at" not in attrs  # timestamps são server-side


def test_chunk_to_model_attrs():
    cid, did = uuid4(), uuid4()
    chunk = DocumentChunk(cid, did, 3, "trecho", [0.1, 0.2])
    attrs = DocumentChunkMapper.to_model_attrs(chunk)
    assert attrs["ordinal"] == 3
    assert attrs["document_id"] == did
    assert attrs["embedding"] == [0.1, 0.2]

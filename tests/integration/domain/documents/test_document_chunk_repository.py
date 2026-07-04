from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.documents.entities.document import Document
from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.repositories.document_repository import DocumentRepository
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository

DIM = 1536


def _vec(seed: float):
    return [seed] + [0.0] * (DIM - 1)


@pytest.mark.asyncio
async def test_search_similar_returns_nearest_approved(db_session):
    now = datetime(2026, 1, 1)
    doc = await DocumentRepository().upsert(
        Document(uuid4(), f"pid-{uuid4()}", "Regras", "c", "https://n", "approved", now, now, None)
    )
    await db_session.flush()

    chunk_repo = DocumentChunkRepository()
    await chunk_repo.replace_for_document(
        doc.uuid,
        [
            DocumentChunk(uuid4(), doc.uuid, 0, "trecho perto", _vec(1.0)),
            DocumentChunk(uuid4(), doc.uuid, 1, "trecho longe", _vec(-1.0)),
        ],
    )
    await db_session.flush()

    hits = await chunk_repo.search_similar(_vec(1.0), top_k=1)
    assert len(hits) == 1
    assert hits[0].content == "trecho perto"
    assert hits[0].citation.title == "Regras"
    assert hits[0].citation.is_notion()

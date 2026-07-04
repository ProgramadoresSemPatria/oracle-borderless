from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.entities.document import Document
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient


@pytest.mark.asyncio
async def test_ingest_persists_document_and_chunks(db_session):
    now = datetime(2026, 1, 1)
    long_content = "parágrafo. " * 400  # força múltiplos chunks
    doc = Document(uuid4(), f"pid-{uuid4()}", "Guia", long_content, "https://n", "approved", now, now, None)

    action = IngestDocumentAction(embeddings=FakeEmbeddingsClient())
    persisted = await action.execute(doc)
    await db_session.flush()

    assert persisted.notion_page_id == doc.notion_page_id
    hits = await DocumentChunkRepository().search_similar([0.1] * 1536, top_k=5)
    assert len(hits) >= 1

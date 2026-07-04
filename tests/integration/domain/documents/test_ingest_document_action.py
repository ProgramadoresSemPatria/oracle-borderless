from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.entities.document import Document
from src.domain.documents.models.document_chunk import DocumentChunkModel
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.domain.documents.repositories.document_repository import DocumentRepository
from src.domain.documents.services.chunking_service import ChunkingService
from src.support.core.exceptions import DomainError
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


@pytest.mark.asyncio
async def test_ingest_rejects_non_approved_document(db_session):
    """Regra 4 (base de conhecimento): documento não aprovado não pode ser ingerido nem persistido."""
    now = datetime(2026, 1, 1)
    page_id = f"pid-{uuid4()}"
    doc = Document(uuid4(), page_id, "Rascunho", "conteúdo qualquer", "https://n", "pending", now, now, None)

    action = IngestDocumentAction(embeddings=FakeEmbeddingsClient())
    with pytest.raises(DomainError):
        await action.execute(doc)
    await db_session.flush()

    persisted = await DocumentRepository().get_by_notion_page_id(page_id)
    assert persisted is None


@pytest.mark.asyncio
async def test_ingest_is_idempotent_and_replaces_chunks(db_session):
    """Re-ingerir a mesma notion_page_id deve atualizar o documento in place e substituir os chunks, sem acumular."""
    now = datetime(2026, 1, 1)
    page_id = f"pid-{uuid4()}"
    old_content = "conteúdo antigo sobre regras antigas. " * 400
    new_content = "conteúdo novo totalmente diferente sobre políticas atuais. " * 400

    action = IngestDocumentAction(embeddings=FakeEmbeddingsClient())

    first_doc = Document(uuid4(), page_id, "Guia", old_content, "https://n", "approved", now, now, None)
    first = await action.execute(first_doc)
    await db_session.flush()

    second_doc = Document(uuid4(), page_id, "Guia", new_content, "https://n", "approved", now, now, None)
    second = await action.execute(second_doc)
    await db_session.flush()

    # upsert: mesma linha (mesmo uuid), não uma linha nova/duplicada.
    assert second.uuid == first.uuid
    assert second.content == new_content

    # chunks substituídos, não acumulados: total de chunks == chunks do conteúdo novo.
    expected_chunks = ChunkingService().split(new_content)
    count_stmt = select(func.count()).select_from(DocumentChunkModel).where(
        DocumentChunkModel.document_id == second.uuid
    )
    total_chunks = (await db_session.execute(count_stmt)).scalar_one()
    assert total_chunks == len(expected_chunks)

    # nenhum chunk remanescente do conteúdo antigo.
    vector = FakeEmbeddingsClient()._vector(expected_chunks[0])
    hits = await DocumentChunkRepository().search_similar(vector, top_k=len(expected_chunks) + 5)
    assert len(hits) == len(expected_chunks)
    assert all("antigo" not in hit.content for hit in hits)
    assert all("novo" in hit.content for hit in hits)

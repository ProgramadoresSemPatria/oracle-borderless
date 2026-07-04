import pytest

from database.seeds.dev_documents_seed import DevDocumentsSeed
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.support.core.context import CurrentAsyncSessionContext


@pytest.mark.asyncio
async def test_seed_ingests_markdown_docs(db_session, monkeypatch):
    # usa embeddings fake para não chamar OpenAI
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient
    import database.seeds.dev_documents_seed as mod
    monkeypatch.setattr(mod, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    await DevDocumentsSeed.seed()
    await db_session.flush()

    hits = await DocumentChunkRepository().search_similar([0.1] * 1536, top_k=3)
    assert len(hits) >= 1

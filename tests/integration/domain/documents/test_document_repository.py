from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.documents.entities.document import Document
from src.domain.documents.repositories.document_repository import DocumentRepository


def _doc(page_id, title="T"):
    now = datetime(2026, 1, 1)
    return Document(uuid4(), page_id, title, "conteúdo", "https://n", "approved", now, now, None)


@pytest.mark.asyncio
async def test_upsert_inserts_then_updates(db_session):
    repo = DocumentRepository()
    created = await repo.upsert(_doc("pid-1", "Original"))
    await db_session.flush()
    assert created.title == "Original"

    updated = await repo.upsert(_doc("pid-1", "Atualizado"))
    await db_session.flush()

    found = await repo.get_by_notion_page_id("pid-1")
    assert found is not None
    assert found.title == "Atualizado"
    assert found.uuid == created.uuid  # mesma linha, não duplicou

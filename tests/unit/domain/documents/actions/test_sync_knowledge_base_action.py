from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.documents.actions.sync_knowledge_base_action import SyncKnowledgeBaseAction
from src.domain.documents.entities.document import Document
from src.support.clients.notion.notion_client import NotionPage


def _dt(day: int) -> datetime:
    return datetime(2026, 7, day, tzinfo=timezone.utc)


def _approved(page_id: str, edited: datetime) -> NotionPage:
    return NotionPage(
        id=page_id, title=f"Doc {page_id}", content="", url="https://n", is_approved=True,
        last_edited_time=edited,
    )


def _existing(page_id: str, edited: datetime | None, deleted: bool = False) -> Document:
    now = _dt(1)
    return Document(
        uuid=uuid4(), notion_page_id=page_id, title=f"Doc {page_id}", content="c",
        source_url="https://n", status="approved", created_at=now, updated_at=now,
        deleted_at=_dt(1) if deleted else None, last_edited_time=edited,
    )


class FakeNotion:
    def __init__(self, approved: list[NotionPage]):
        self._approved = approved

    async def list_approved_pages(self) -> list[NotionPage]:
        return self._approved

    async def get_page(self, page_id: str) -> NotionPage:
        page = next(p for p in self._approved if p.id == page_id)
        return NotionPage(page.id, page.title, "conteúdo completo", page.url, True, page.last_edited_time)


class FakeIngest:
    def __init__(self):
        self.executed: list[str] = []

    async def execute(self, document: Document) -> Document:
        self.executed.append(document.notion_page_id)
        return document


class FakeDocRepo:
    def __init__(self, existing: list[Document]):
        self._existing = existing
        self.soft_deleted: list[str] = []

    async def list_all(self) -> list[Document]:
        return list(self._existing)

    async def soft_delete_by_page_id(self, page_id: str, when: datetime) -> None:
        self.soft_deleted.append(page_id)


class FakeChunkRepo:
    def __init__(self):
        self.cleared: list = []

    async def replace_for_document(self, document_id, chunks) -> None:
        self.cleared.append(document_id)


def _action(notion, ingest, docs, chunks) -> SyncKnowledgeBaseAction:
    return SyncKnowledgeBaseAction(notion=notion, ingest=ingest, documents=docs, chunks=chunks)


@pytest.mark.asyncio
async def test_new_page_is_ingested():
    notion = FakeNotion([_approved("a", _dt(5))])
    ingest = FakeIngest()
    action = _action(notion, ingest, FakeDocRepo([]), FakeChunkRepo())
    report = await action.execute()
    assert ingest.executed == ["a"]
    assert report.ingested == 1 and report.total_approved == 1


@pytest.mark.asyncio
async def test_unchanged_page_is_skipped():
    notion = FakeNotion([_approved("a", _dt(5))])
    ingest = FakeIngest()
    action = _action(notion, ingest, FakeDocRepo([_existing("a", _dt(5))]), FakeChunkRepo())
    report = await action.execute()
    assert ingest.executed == []
    assert report.skipped == 1 and report.ingested == 0


@pytest.mark.asyncio
async def test_edited_page_is_reingested():
    notion = FakeNotion([_approved("a", _dt(9))])  # mais novo
    ingest = FakeIngest()
    action = _action(notion, ingest, FakeDocRepo([_existing("a", _dt(5))]), FakeChunkRepo())
    report = await action.execute()
    assert ingest.executed == ["a"] and report.ingested == 1


@pytest.mark.asyncio
async def test_page_out_of_scope_is_removed():
    notion = FakeNotion([_approved("a", _dt(5))])  # 'b' não está mais aprovado
    ingest = FakeIngest()
    stale = _existing("b", _dt(5))
    docs = FakeDocRepo([_existing("a", _dt(5)), stale])
    chunks = FakeChunkRepo()
    report = await _action(notion, ingest, docs, chunks).execute()
    assert docs.soft_deleted == ["b"]
    assert stale.uuid in chunks.cleared
    assert report.removed == 1


@pytest.mark.asyncio
async def test_already_deleted_page_not_removed_again():
    notion = FakeNotion([_approved("a", _dt(5))])
    docs = FakeDocRepo([_existing("a", _dt(5)), _existing("b", _dt(5), deleted=True)])
    chunks = FakeChunkRepo()
    report = await _action(notion, FakeIngest(), docs, chunks).execute()
    assert docs.soft_deleted == [] and report.removed == 0


@pytest.mark.asyncio
async def test_limit_bounds_ingestion_and_skips_removal():
    notion = FakeNotion([_approved("a", _dt(5)), _approved("b", _dt(5)), _approved("c", _dt(5))])
    ingest = FakeIngest()
    # 'z' está no banco e fora do aprovado — NÃO deve ser removido num run limitado.
    docs = FakeDocRepo([_existing("z", _dt(5))])
    report = await _action(notion, ingest, docs, FakeChunkRepo()).execute(limit=2)
    assert len(ingest.executed) == 2
    assert docs.soft_deleted == [] and report.removed == 0


@pytest.mark.asyncio
async def test_limit_advances_past_already_ingested_pages():
    """Blocos repetidos devem AVANÇAR: --limit conta ingestões novas, pula as já feitas."""
    notion = FakeNotion([
        _approved("a", _dt(5)), _approved("b", _dt(5)),
        _approved("c", _dt(5)), _approved("d", _dt(5)),
    ])
    ingest = FakeIngest()
    # a, b já ingeridos e inalterados → devem ser pulados; limit 2 deve pegar c, d.
    docs = FakeDocRepo([_existing("a", _dt(5)), _existing("b", _dt(5))])
    report = await _action(notion, ingest, docs, FakeChunkRepo()).execute(limit=2)
    assert ingest.executed == ["c", "d"]
    assert report.ingested == 2 and report.skipped == 2


@pytest.mark.asyncio
async def test_force_reingests_even_when_unchanged():
    notion = FakeNotion([_approved("a", _dt(5))])
    ingest = FakeIngest()
    action = _action(notion, ingest, FakeDocRepo([_existing("a", _dt(5))]), FakeChunkRepo())
    report = await action.execute(force=True)
    assert ingest.executed == ["a"] and report.ingested == 1

# Milestone 1 — Oráculo (fatia vertical) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o caminho ponta-a-ponta do oráculo: pergunta → RAG na base (Notion, pgvector) + web search agêntico → resposta fundamentada e citada, em streaming (SSE), com UI web mínima.

**Architecture:** RAG clássico para a base de conhecimento (recuperação no endpoint, com a sessão de DB viva) + tools agênticas HTTP (`web_search`, `fetch_notion_page`) durante o streaming. O motor Pydantic AI vive atrás do `OracleEnginePort` (ADR-0007); o domínio nunca importa `pydantic_ai`. Persistência em Postgres + pgvector (HNSW cosine). Stateless: histórico vem no request.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async (asyncpg), Alembic, pgvector (HNSW), Pydantic AI, OpenAI embeddings (`text-embedding-3-small`), Anthropic/OpenAI (chat, selecionável), Tavily (web search), Notion via MCP.

## Global Constraints

Copiadas verbatim do CLAUDE.md e do spec — valem para TODA task:

- **Domain não importa infraestrutura.** `entities/` não importam `sqlalchemy`/`fastapi`/`pydantic`. Nenhum arquivo de domínio importa `pydantic_ai` — só via `OracleEnginePort`.
- **Entity (dataclass pura) ≠ Model (SQLAlchemy).** Conversão só no Mapper do subdomínio, nunca inline no Repository.
- **Sessão de DB vem do contexto:** `CurrentAsyncSessionContext.get()`. Nunca criar `AsyncSessionLocal()` em controller/action/repository.
- **Nada confidencial na base.** Ingestão só aceita documentos com `is_approved()`; respostas só citam fontes aprovadas ou web search explícito.
- **Controllers finos:** recebem request, chamam UMA Action, retornam Response. Composição é responsabilidade de Action (Action chama Action).
- **Sem Service agregador.** Cada caso de uso é uma Action.
- **Schemas Pydantic em `src/app/api/`; DTOs internos em `src/domain/{ctx}/dtos/`** (dataclasses).
- **Jobs/ingestão idempotentes.** Re-ingerir a mesma `notion_page_id` substitui, não duplica.
- **Seeds com tracking** em `database/seeds/__init__.py`.
- **Não introduzir dependências novas** (todas já estão no `pyproject.toml`).
- **Auth:** Cloudflare Access (edge). App não implementa auth; endpoint é `public_router`.
- **Config:** `EMBEDDING_DIM=1536`, `RAG_TOP_K=6`, `RAG_CHUNK_SIZE=1200`, `RAG_CHUNK_OVERLAP=200`, `LLM_PROVIDER` ∈ {anthropic, openai}.
- **Testes:** `pytest` com `asyncio_mode=auto`. Testes de integração exigem Postgres+pgvector rodando (`docker compose -f docker/docker-compose.yml up -d`) e o banco `oracle_borderless_test`.

---

## File Structure

**Criar:**
- `src/domain/documents/entities/document.py` — `Document` (dataclass).
- `src/domain/documents/entities/document_chunk.py` — `DocumentChunk` (dataclass).
- `src/domain/documents/models/document.py` — `DocumentModel`.
- `src/domain/documents/models/document_chunk.py` — `DocumentChunkModel` (coluna `Vector`).
- `src/domain/documents/mappers/document_mapper.py`, `document_chunk_mapper.py`.
- `src/domain/documents/repositories/document_repository.py`, `document_chunk_repository.py`.
- `src/domain/documents/dtos/knowledge_snippet.py` — reexport do tipo de fronteira (ver Task 1).
- `src/domain/documents/actions/ingest_document_action.py`, `search_knowledge_base_action.py`.
- `src/domain/documents/mappers/notion_page_mapper.py` — `NotionPage` → `Document`.
- `src/domain/conversations/actions/answer_question_action.py`.
- `src/support/agent/oracle_engine.py` — motor real Pydantic AI + `get_oracle_engine()`.
- `src/support/agent/tools.py` — tools HTTP (`web_search`, `fetch_notion_page`) + helpers de formatação.
- `src/app/api/requests/ask_question_request.py`.
- `src/app/api/controllers/conversation_controller.py`.
- `src/app/api/routes/conversations.py`.
- `src/app/web/index.html` + `src/app/api/routes/web.py` (serve a UI).
- `src/app/console/commands/knowledge_ingest_command.py`.
- `database/seeds/dev_documents_seed.py` + `database/seeds/knowledge/*.md`.
- `database/migrations/versions/0001_documents_pgvector.py`.
- `.env.example`.
- Testes espelhando cada componente em `tests/unit/...` e `tests/integration/...`; `tests/integration/conftest.py`; fakes em `tests/fakes/`.

**Modificar:**
- `docker/docker-compose.yml` — imagem `pgvector/pgvector:pg16`.
- `src/support/agent/ports.py` — adicionar `KnowledgeSnippet` e o parâmetro `knowledge` em `stream_answer`.
- `tests/fakes/fake_oracle_engine.py` — nova assinatura.
- `database/seeds/__init__.py` — registrar `DevDocumentsSeed`.

---

### Task 1: Fronteira — `KnowledgeSnippet` no port + atualizar assinatura de `stream_answer`

**Files:**
- Modify: `src/support/agent/ports.py`
- Modify: `tests/fakes/fake_oracle_engine.py`
- Test: `tests/unit/support/agent/test_ports.py`

**Interfaces:**
- Produces:
  - `KnowledgeSnippet(content: str, citation: Citation)` — dataclass em `ports.py`.
  - `OracleEnginePort.stream_answer(question: str, history: list[AgentMessage], knowledge: list[KnowledgeSnippet]) -> AsyncIterator[AgentStreamChunk]`.

- [ ] **Step 1: Escrever o teste que falha**

Adicione a `tests/unit/support/agent/test_ports.py`:

```python
import pytest

from src.support.agent.ports import AgentMessage, KnowledgeSnippet
from src.domain.shared.value_objects.citation import Citation
from tests.fakes.fake_oracle_engine import FakeOracleEngine


def test_knowledge_snippet_carries_content_and_citation():
    snip = KnowledgeSnippet(
        content="texto",
        citation=Citation("notion", "Doc", "https://n/a", "trecho", "pid"),
    )
    assert snip.content == "texto"
    assert snip.citation.is_notion()


@pytest.mark.asyncio
async def test_fake_engine_accepts_knowledge_argument():
    engine = FakeOracleEngine(answer="ola mundo")
    snippets = [KnowledgeSnippet("ctx", Citation("notion", "D", "u", "s", "p"))]
    chunks = [c async for c in engine.stream_answer("q?", [], snippets)]
    assert any(c.type == "text" for c in chunks)
    assert any(c.type == "sources" for c in chunks)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/unit/support/agent/test_ports.py -v`
Expected: FAIL (`ImportError: cannot import name 'KnowledgeSnippet'`).

- [ ] **Step 3: Implementar**

Em `src/support/agent/ports.py`, adicione o dataclass e ajuste o Protocol:

```python
@dataclass
class KnowledgeSnippet:
    """Trecho recuperado da base (RAG clássico), com sua fonte para citação."""

    content: str
    citation: Citation


class OracleEnginePort(Protocol):
    def stream_answer(
        self,
        question: str,
        history: list[AgentMessage],
        knowledge: list[KnowledgeSnippet],
    ) -> AsyncIterator[AgentStreamChunk]: ...
```

Em `tests/fakes/fake_oracle_engine.py`, atualize a assinatura:

```python
    async def stream_answer(
        self,
        question: str,
        history: list[AgentMessage],
        knowledge: list["KnowledgeSnippet"] | None = None,
    ) -> AsyncIterator[AgentStreamChunk]:
        for token in self._answer.split():
            yield AgentStreamChunk(type="text", text=token + " ")
        cites = [s.citation for s in (knowledge or [])] or self._citations
        yield AgentStreamChunk(type="sources", citations=cites)
```

Adicione o import no topo do fake: `from src.support.agent.ports import AgentMessage, AgentStreamChunk, KnowledgeSnippet`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/unit/support/agent/test_ports.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/support/agent/ports.py tests/fakes/fake_oracle_engine.py tests/unit/support/agent/test_ports.py
git commit -m "feat(agent): KnowledgeSnippet no port + knowledge em stream_answer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Entities de `documents`

**Files:**
- Create: `src/domain/documents/entities/document.py`, `src/domain/documents/entities/document_chunk.py`
- Test: `tests/unit/domain/documents/entities/test_document.py`

**Interfaces:**
- Produces:
  - `Document(uuid, notion_page_id, title, content, source_url, status, created_at, updated_at, deleted_at=None)` com `is_approved() -> bool`.
  - `DocumentChunk(uuid, document_id, ordinal, content, embedding: list[float] | None = None)`.

- [ ] **Step 1: Teste que falha**

`tests/unit/domain/documents/entities/test_document.py` (crie também `__init__.py` nas pastas novas de teste):

```python
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
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/domain/documents/entities/ -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/documents/entities/document.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Document:
    """Entidade de domínio. Pura. Sem SQLAlchemy."""

    uuid: UUID
    notion_page_id: str
    title: str
    content: str
    source_url: str
    status: str  # "approved" | "pending" | "archived"
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_approved(self) -> bool:
        return self.status == "approved" and self.deleted_at is None
```

`src/domain/documents/entities/document_chunk.py`:

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass
class DocumentChunk:
    """Trecho de um Document, com seu vetor de embedding. Domínio puro."""

    uuid: UUID
    document_id: UUID
    ordinal: int
    content: str
    embedding: list[float] | None = None
```

- [ ] **Step 4: Ver passar**

Run: `pytest tests/unit/domain/documents/entities/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/documents/entities tests/unit/domain/documents/entities
git commit -m "feat(documents): entities Document + DocumentChunk

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Models + Mappers de `documents`

**Files:**
- Create: `src/domain/documents/models/document.py`, `src/domain/documents/models/document_chunk.py`
- Create: `src/domain/documents/mappers/document_mapper.py`, `src/domain/documents/mappers/document_chunk_mapper.py`
- Modify: `src/domain/documents/mappers/__init__.py`
- Test: `tests/unit/domain/documents/mappers/test_mappers.py`

**Interfaces:**
- Consumes: `Document`, `DocumentChunk` (Task 2).
- Produces:
  - `DocumentModel` (`__tablename__="documents"`), `DocumentChunkModel` (`__tablename__="document_chunks"`, coluna `embedding` = `Vector(settings.EMBEDDING_DIM)`).
  - `DocumentMapper.to_entity(model) -> Document`, `DocumentMapper.to_model_attrs(entity) -> dict`.
  - `DocumentChunkMapper.to_entity(model) -> DocumentChunk`, `DocumentChunkMapper.to_model_attrs(entity) -> dict`.

- [ ] **Step 1: Teste que falha**

`tests/unit/domain/documents/mappers/test_mappers.py`:

```python
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
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/domain/documents/mappers/ -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar models**

`src/domain/documents/models/document.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import ApplyRelations, HasTimestamps, HasUUID
from src.support.core.models.base_model import BaseModel


class DocumentModel(BaseModel, HasUUID, HasTimestamps, ApplyRelations):
    __tablename__ = "documents"

    notion_page_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(20), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`src/domain/documents/models/document_chunk.py`:

```python
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import HasTimestamps, HasUUID
from src.support.core.models.base_model import BaseModel
from src.support.core.settings import settings


class DocumentChunkModel(BaseModel, HasUUID, HasTimestamps):
    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.uuid", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.EMBEDDING_DIM), nullable=True
    )
```

- [ ] **Step 4: Implementar mappers**

`src/domain/documents/mappers/document_mapper.py`:

```python
from src.domain.documents.entities.document import Document
from src.domain.documents.models.document import DocumentModel


class DocumentMapper:
    @staticmethod
    def to_entity(model: DocumentModel) -> Document:
        return Document(
            uuid=model.uuid,
            notion_page_id=model.notion_page_id,
            title=model.title,
            content=model.content,
            source_url=model.source_url,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model_attrs(entity: Document) -> dict:
        return {
            "uuid": entity.uuid,
            "notion_page_id": entity.notion_page_id,
            "title": entity.title,
            "content": entity.content,
            "source_url": entity.source_url,
            "status": entity.status,
            "deleted_at": entity.deleted_at,
        }
```

`src/domain/documents/mappers/document_chunk_mapper.py`:

```python
from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.models.document_chunk import DocumentChunkModel


class DocumentChunkMapper:
    @staticmethod
    def to_entity(model: DocumentChunkModel) -> DocumentChunk:
        return DocumentChunk(
            uuid=model.uuid,
            document_id=model.document_id,
            ordinal=model.ordinal,
            content=model.content,
            embedding=list(model.embedding) if model.embedding is not None else None,
        )

    @staticmethod
    def to_model_attrs(entity: DocumentChunk) -> dict:
        return {
            "uuid": entity.uuid,
            "document_id": entity.document_id,
            "ordinal": entity.ordinal,
            "content": entity.content,
            "embedding": entity.embedding,
        }
```

Atualize `src/domain/documents/mappers/__init__.py`:

```python
from src.domain.documents.mappers.document_mapper import DocumentMapper
from src.domain.documents.mappers.document_chunk_mapper import DocumentChunkMapper

__all__ = ["DocumentMapper", "DocumentChunkMapper"]
```

- [ ] **Step 5: Ver passar**

Run: `pytest tests/unit/domain/documents/mappers/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/domain/documents/models src/domain/documents/mappers tests/unit/domain/documents/mappers
git commit -m "feat(documents): models + mappers (DocumentModel, DocumentChunkModel c/ pgvector)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Infra pgvector + migration + harness de integração

**Files:**
- Modify: `docker/docker-compose.yml`
- Create: `database/migrations/versions/0001_documents_pgvector.py`
- Create: `tests/integration/conftest.py`
- Test: `tests/integration/test_migration_pgvector.py`

**Interfaces:**
- Produces: tabelas `documents`, `document_chunks` (com extensão `vector` e índice HNSW cosine); fixture `db_session` (async, com `CurrentAsyncSessionContext` setado) para os testes de integração.

- [ ] **Step 1: Trocar a imagem do Postgres**

Em `docker/docker-compose.yml`, troque `image: postgres:16-alpine` por:

```yaml
    image: pgvector/pgvector:pg16
```

Suba e crie o banco de teste:

```bash
docker compose -f docker/docker-compose.yml up -d
docker exec oracle_borderless_db createdb -U oracle oracle_borderless_test
```

- [ ] **Step 2: Escrever a migration (à mão, não autogenerate)**

`database/migrations/versions/0001_documents_pgvector.py`:

```python
"""documents + document_chunks com pgvector (HNSW cosine)

Revision ID: 0001_documents_pgvector
Revises:
Create Date: 2026-07-04
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0001_documents_pgvector"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536  # settings.EMBEDDING_DIM (snapshot na migration)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column("notion_page_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_notion_page_id", "documents", ["notion_page_id"], unique=True)
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
```

- [ ] **Step 3: Aplicar a migration**

Run: `alembic upgrade head`
Expected: sem erro. Verifique: `alembic current` mostra `0001_documents_pgvector`.

- [ ] **Step 4: Harness de integração (conftest)**

`tests/integration/conftest.py`:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.settings import settings


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.database_url_async_test, poolclass=None)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        CurrentAsyncSessionContext.set(session)
        try:
            yield session
            await session.rollback()
        finally:
            CurrentAsyncSessionContext.clear()
    await engine.dispose()
```

`tests/integration/test_migration_pgvector.py`:

```python
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_vector_extension_and_tables_exist(db_session):
    ext = await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'"))
    assert ext.scalar_one() == 1

    for table in ("documents", "document_chunks"):
        r = await db_session.execute(text("SELECT to_regclass(:t)"), {"t": table})
        assert r.scalar_one() is not None
```

- [ ] **Step 5: Rodar integração**

Run: `pytest tests/integration/test_migration_pgvector.py -v`
Expected: PASS (com o banco de teste já migrado — rode `DB_NAME=oracle_borderless_test alembic upgrade head` se ainda não migrou o de teste, ou aplique a migration no banco de teste conforme o database-guide).

- [ ] **Step 6: Commit**

```bash
git add docker/docker-compose.yml database/migrations/versions/0001_documents_pgvector.py tests/integration/conftest.py tests/integration/test_migration_pgvector.py
git commit -m "feat(db): imagem pgvector + migration documents/document_chunks (HNSW cosine)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `DocumentRepository`

**Files:**
- Create: `src/domain/documents/repositories/document_repository.py`
- Modify: `src/domain/documents/repositories/__init__.py`
- Test: `tests/integration/domain/documents/test_document_repository.py`

**Interfaces:**
- Consumes: `Document`, `DocumentMapper`, `CurrentAsyncSessionContext`.
- Produces:
  - `DocumentRepository.upsert(document: Document) -> Document` — insere por `notion_page_id`, ou atualiza se já existe (idempotente).
  - `DocumentRepository.get_by_notion_page_id(page_id: str) -> Document | None`.

- [ ] **Step 1: Teste (integração) que falha**

`tests/integration/domain/documents/test_document_repository.py`:

```python
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
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/integration/domain/documents/test_document_repository.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/documents/repositories/document_repository.py`:

```python
from uuid import UUID

from sqlalchemy import select

from src.domain.documents.entities.document import Document
from src.domain.documents.mappers import DocumentMapper
from src.domain.documents.models.document import DocumentModel
from src.support.core.context import CurrentAsyncSessionContext


class DocumentRepository:
    def __init__(self) -> None:
        self.session = CurrentAsyncSessionContext.get()

    async def get_by_notion_page_id(self, page_id: str) -> Document | None:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.notion_page_id == page_id)
        )
        model = result.scalar_one_or_none()
        return DocumentMapper.to_entity(model) if model else None

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.uuid == document_id)
        )
        model = result.scalar_one_or_none()
        return DocumentMapper.to_entity(model) if model else None

    async def upsert(self, document: Document) -> Document:
        result = await self.session.execute(
            select(DocumentModel).where(DocumentModel.notion_page_id == document.notion_page_id)
        )
        model = result.scalar_one_or_none()
        attrs = DocumentMapper.to_model_attrs(document)
        if model is None:
            model = DocumentModel(**attrs)
            self.session.add(model)
        else:
            for key in ("title", "content", "source_url", "status", "deleted_at"):
                setattr(model, key, attrs[key])
        await self.session.flush()
        await self.session.refresh(model)
        return DocumentMapper.to_entity(model)
```

Atualize `src/domain/documents/repositories/__init__.py` para exportar `DocumentRepository`.

- [ ] **Step 4: Ver passar**

Run: `pytest tests/integration/domain/documents/test_document_repository.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/documents/repositories tests/integration/domain/documents/test_document_repository.py
git commit -m "feat(documents): DocumentRepository (upsert idempotente por notion_page_id)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `DocumentChunkRepository` (persistência + busca vetorial)

**Files:**
- Create: `src/domain/documents/repositories/document_chunk_repository.py`
- Modify: `src/domain/documents/repositories/__init__.py`
- Test: `tests/integration/domain/documents/test_document_chunk_repository.py`

**Interfaces:**
- Consumes: `DocumentChunk`, `DocumentChunkMapper`, `DocumentModel`, `KnowledgeSnippet`, `Citation`.
- Produces:
  - `DocumentChunkRepository.replace_for_document(document_id: UUID, chunks: list[DocumentChunk]) -> None`.
  - `DocumentChunkRepository.search_similar(embedding: list[float], top_k: int) -> list[KnowledgeSnippet]` — join com `documents` (só `approved`, não deletados), ordenado por distância cosseno.

- [ ] **Step 1: Teste (integração) que falha**

`tests/integration/domain/documents/test_document_chunk_repository.py`:

```python
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
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/integration/domain/documents/test_document_chunk_repository.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/documents/repositories/document_chunk_repository.py`:

```python
from uuid import UUID

from sqlalchemy import delete, select

from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.mappers import DocumentChunkMapper
from src.domain.documents.models.document import DocumentModel
from src.domain.documents.models.document_chunk import DocumentChunkModel
from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.settings import settings


class DocumentChunkRepository:
    def __init__(self) -> None:
        self.session = CurrentAsyncSessionContext.get()

    async def replace_for_document(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        await self.session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        )
        for chunk in chunks:
            self.session.add(DocumentChunkModel(**DocumentChunkMapper.to_model_attrs(chunk)))
        await self.session.flush()

    async def search_similar(
        self, embedding: list[float], top_k: int | None = None
    ) -> list[KnowledgeSnippet]:
        limit = top_k if top_k is not None else settings.RAG_TOP_K
        stmt = (
            select(
                DocumentChunkModel.content,
                DocumentModel.title,
                DocumentModel.source_url,
                DocumentModel.notion_page_id,
            )
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.uuid)
            .where(DocumentModel.status == "approved", DocumentModel.deleted_at.is_(None))
            .order_by(DocumentChunkModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            KnowledgeSnippet(
                content=row.content,
                citation=Citation(
                    source_type="notion",
                    title=row.title,
                    url=row.source_url,
                    snippet=row.content[:200],
                    page_id=row.notion_page_id,
                ),
            )
            for row in rows
        ]
```

Atualize `repositories/__init__.py` para exportar `DocumentChunkRepository`.

- [ ] **Step 4: Ver passar**

Run: `pytest tests/integration/domain/documents/test_document_chunk_repository.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/documents/repositories tests/integration/domain/documents/test_document_chunk_repository.py
git commit -m "feat(documents): DocumentChunkRepository (replace + search_similar cosine)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `IngestDocumentAction`

**Files:**
- Create: `src/domain/documents/actions/ingest_document_action.py`
- Modify: `src/domain/documents/actions/__init__.py`
- Test: `tests/integration/domain/documents/test_ingest_document_action.py`

**Interfaces:**
- Consumes: `Document`, `ChunkingService`, `EmbeddingsClient`, `DocumentRepository`, `DocumentChunkRepository`, `DocumentChunk`.
- Produces: `IngestDocumentAction(embeddings: EmbeddingsClient).execute(document: Document) -> Document`.

- [ ] **Step 1: Teste (integração) que falha**

`tests/integration/domain/documents/test_ingest_document_action.py`:

```python
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
```

> Confirme que `tests/fakes/fake_embeddings_client.py` (já existe) retorna vetores de dimensão 1536. Se não, ajuste o fake para `[0.1] * settings.EMBEDDING_DIM` por texto.

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/integration/domain/documents/test_ingest_document_action.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/documents/actions/ingest_document_action.py`:

```python
from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.repositories.document_repository import DocumentRepository
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.domain.documents.services.chunking_service import ChunkingService
from src.support.clients.embeddings.embeddings_client import EmbeddingsClient
from src.support.core.exceptions import DomainError


class IngestDocumentAction:
    """Ingere um Document aprovado na base: chunking → embeddings → persistência.

    Idempotente: re-ingerir a mesma notion_page_id substitui documento e chunks.
    Source-agnostic: o Document já vem montado (Notion MCP ou seed).
    """

    def __init__(self, embeddings: EmbeddingsClient) -> None:
        self.embeddings = embeddings
        self.chunking = ChunkingService()
        self.documents = DocumentRepository()
        self.chunks = DocumentChunkRepository()

    async def execute(self, document: Document) -> Document:
        if not document.is_approved():
            raise DomainError("Documento não aprovado não pode ser ingerido na base.")

        persisted = await self.documents.upsert(document)

        texts = self.chunking.split(document.content)
        vectors = await self.embeddings.embed(texts)
        entities = [
            DocumentChunk(
                uuid=uuid4(),
                document_id=persisted.uuid,
                ordinal=i,
                content=text,
                embedding=vectors[i],
            )
            for i, text in enumerate(texts)
        ]
        await self.chunks.replace_for_document(persisted.uuid, entities)
        return persisted
```

> Verifique o nome da exceção base em `src/support/core/exceptions.py`. Se não houver `DomainError`, use a exceção base existente (ex.: `DomainException`) — ajuste o import e o raise conforme o que existe no arquivo.

- [ ] **Step 4: Ver passar**

Run: `pytest tests/integration/domain/documents/test_ingest_document_action.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/documents/actions tests/integration/domain/documents/test_ingest_document_action.py
git commit -m "feat(documents): IngestDocumentAction (chunk+embed+persist, idempotente)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Fake do `NotionClient` + `NotionPageMapper` + command `knowledge:ingest`

**Files:**
- Create: `src/domain/documents/mappers/notion_page_mapper.py`
- Create: `tests/fakes/fake_notion_client.py`
- Create: `src/app/console/commands/knowledge_ingest_command.py`
- Test: `tests/unit/domain/documents/mappers/test_notion_page_mapper.py`

**Interfaces:**
- Consumes: `NotionPage` (do `NotionClient`), `Document`.
- Produces:
  - `NotionPageMapper.to_document(page: NotionPage) -> Document`.
  - `FakeNotionClient(pages: dict[str, NotionPage]).get_page(page_id) -> NotionPage`.
  - Command `knowledge:ingest {page_id:str}`.

- [ ] **Step 1: Teste que falha**

`tests/unit/domain/documents/mappers/test_notion_page_mapper.py`:

```python
from src.domain.documents.mappers.notion_page_mapper import NotionPageMapper
from src.support.clients.notion.notion_client import NotionPage


def test_approved_page_maps_to_approved_document():
    page = NotionPage(id="pid", title="T", content="C", url="https://n", is_approved=True)
    doc = NotionPageMapper.to_document(page)
    assert doc.notion_page_id == "pid"
    assert doc.status == "approved"
    assert doc.is_approved()


def test_unapproved_page_maps_to_pending():
    page = NotionPage(id="pid", title="T", content="C", url="https://n", is_approved=False)
    assert NotionPageMapper.to_document(page).status == "pending"
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/domain/documents/mappers/test_notion_page_mapper.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar mapper**

`src/domain/documents/mappers/notion_page_mapper.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.support.clients.notion.notion_client import NotionPage


class NotionPageMapper:
    @staticmethod
    def to_document(page: NotionPage) -> Document:
        now = datetime.now(timezone.utc)
        return Document(
            uuid=uuid4(),
            notion_page_id=page.id,
            title=page.title,
            content=page.content,
            source_url=page.url,
            status="approved" if page.is_approved else "pending",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
```

- [ ] **Step 4: Fake do NotionClient**

`tests/fakes/fake_notion_client.py`:

```python
from src.support.clients.notion.notion_client import NotionPage


class FakeNotionClient:
    def __init__(self, pages: dict[str, NotionPage] | None = None) -> None:
        self._pages = pages or {}

    async def get_page(self, page_id: str) -> NotionPage:
        if page_id not in self._pages:
            raise KeyError(f"página {page_id} não encontrada no fake")
        return self._pages[page_id]

    async def list_approved_pages(self) -> list[NotionPage]:
        return [p for p in self._pages.values() if p.is_approved]
```

- [ ] **Step 5: Command `knowledge:ingest`**

`src/app/console/commands/knowledge_ingest_command.py`:

```python
from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.mappers.notion_page_mapper import NotionPageMapper
from src.support.clients.embeddings.embeddings_client import get_embeddings_client
from src.support.clients.notion.notion_client import NotionClient
from src.support.core.console.command import Command
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal


class KnowledgeIngestCommand(Command):
    signature = "knowledge:ingest {page_id:str}"
    description = "Ingere uma página aprovada do Notion (MCP) na base de conhecimento."

    async def handle(self) -> None:
        page_id = self.input["page_id"]
        async with AsyncSessionLocal() as session:
            CurrentAsyncSessionContext.set(session)
            try:
                page = await NotionClient().get_page(page_id)
                document = NotionPageMapper.to_document(page)
                action = IngestDocumentAction(embeddings=get_embeddings_client())
                result = await action.execute(document)
                await session.commit()
                print(f"Ingerido: {result.title} ({result.notion_page_id})")
            except Exception:
                await session.rollback()
                raise
            finally:
                CurrentAsyncSessionContext.clear()
```

> Nota: comandos CLI rodam **fora** do request, então não há sessão no contexto — por isso o command abre e gerencia a própria sessão explicitamente. Isso é o padrão para console/jobs (a regra 3 se aplica a controller/action/repository no fluxo HTTP), consistente com como seeds e jobs operam.

- [ ] **Step 6: Ver passar (mapper) + smoke do command**

Run: `pytest tests/unit/domain/documents/mappers/test_notion_page_mapper.py -v`
Expected: PASS.
Run: `python cli.py list | grep knowledge:ingest`
Expected: o comando aparece na lista.

- [ ] **Step 7: Commit**

```bash
git add src/domain/documents/mappers/notion_page_mapper.py tests/fakes/fake_notion_client.py src/app/console/commands/knowledge_ingest_command.py tests/unit/domain/documents/mappers/test_notion_page_mapper.py
git commit -m "feat(documents): NotionPageMapper + fake NotionClient + command knowledge:ingest

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Seed de documentos dev (markdown)

**Files:**
- Create: `database/seeds/knowledge/regras-do-ecossistema.md`, `database/seeds/knowledge/onboarding.md`
- Create: `database/seeds/dev_documents_seed.py`
- Modify: `database/seeds/__init__.py`
- Test: `tests/integration/database/test_dev_documents_seed.py`

**Interfaces:**
- Consumes: `IngestDocumentAction`, `Document`, `get_embeddings_client`.
- Produces: `DevDocumentsSeed.seed()` (async staticmethod) — ingere os markdown de `database/seeds/knowledge/` como documentos aprovados.

- [ ] **Step 1: Criar os markdown**

`database/seeds/knowledge/regras-do-ecossistema.md` (exemplo mínimo — o conteúdo real virá do Notion depois):

```markdown
# Regras do Ecossistema

Os alunos avançam por trilhas. A trilha inicial é o Onboarding.
O suporte responde em até 24 horas úteis.
```

`database/seeds/knowledge/onboarding.md`:

```markdown
# Onboarding

O onboarding leva em média 7 dias. Ao final, o aluno recebe acesso à comunidade.
```

- [ ] **Step 2: Teste (integração) que falha**

`tests/integration/database/test_dev_documents_seed.py`:

```python
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
```

- [ ] **Step 3: Ver falhar**

Run: `pytest tests/integration/database/test_dev_documents_seed.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implementar seed**

`database/seeds/dev_documents_seed.py`:

```python
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.entities.document import Document
from src.support.clients.embeddings.embeddings_client import get_embeddings_client

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


class DevDocumentsSeed:
    """Ingere os markdown de database/seeds/knowledge/ como docs aprovados (dev/test)."""

    @staticmethod
    async def seed() -> None:
        action = IngestDocumentAction(embeddings=get_embeddings_client())
        now = datetime.now(timezone.utc)
        for path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            title = content.splitlines()[0].lstrip("# ").strip() if content else path.stem
            document = Document(
                uuid=uuid4(),
                notion_page_id=f"seed:{path.stem}",
                title=title,
                content=content,
                source_url=f"seed://{path.name}",
                status="approved",
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            await action.execute(document)
```

Registre em `database/seeds/__init__.py` dentro de `_collect_seeders()` no bloco `ENVIRONMENT == "development"`:

```python
    if settings.ENVIRONMENT == "development":
        from database.seeds.dev_documents_seed import DevDocumentsSeed
        seeders.append(DevDocumentsSeed)
```

- [ ] **Step 5: Ver passar**

Run: `pytest tests/integration/database/test_dev_documents_seed.py -v`
Expected: PASS. (Crie `tests/integration/database/__init__.py` se necessário.)

- [ ] **Step 6: Commit**

```bash
git add database/seeds tests/integration/database
git commit -m "feat(seeds): DevDocumentsSeed ingere markdown de knowledge/ (dev/test)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: `SearchKnowledgeBaseAction`

**Files:**
- Create: `src/domain/documents/actions/search_knowledge_base_action.py`
- Modify: `src/domain/documents/actions/__init__.py`
- Test: `tests/unit/domain/documents/actions/test_search_knowledge_base_action.py`

**Interfaces:**
- Consumes: `EmbeddingsClient`, `DocumentChunkRepository`, `KnowledgeSnippet`.
- Produces: `SearchKnowledgeBaseAction(embeddings, chunk_repo=None).execute(query: str, top_k: int | None = None) -> list[KnowledgeSnippet]`.

> `chunk_repo` é injetável para teste unitário (default: instancia `DocumentChunkRepository()` — que exige sessão no contexto). No teste unitário passamos um fake.

- [ ] **Step 1: Teste (unit) que falha**

`tests/unit/domain/documents/actions/test_search_knowledge_base_action.py`:

```python
import pytest

from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient


class _FakeChunkRepo:
    def __init__(self):
        self.called_with = None

    async def search_similar(self, embedding, top_k=None):
        self.called_with = (embedding, top_k)
        return [KnowledgeSnippet("ctx", Citation("notion", "D", "u", "s", "p"))]


@pytest.mark.asyncio
async def test_search_embeds_query_and_returns_snippets():
    repo = _FakeChunkRepo()
    action = SearchKnowledgeBaseAction(embeddings=FakeEmbeddingsClient(), chunk_repo=repo)
    hits = await action.execute("como funciona o onboarding?", top_k=3)
    assert len(hits) == 1 and hits[0].content == "ctx"
    assert repo.called_with[1] == 3
    assert len(repo.called_with[0]) == 1536  # vetor da query
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/domain/documents/actions/test_search_knowledge_base_action.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/documents/actions/search_knowledge_base_action.py`:

```python
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.support.agent.ports import KnowledgeSnippet
from src.support.clients.embeddings.embeddings_client import EmbeddingsClient


class SearchKnowledgeBaseAction:
    """RAG clássico: embed da query → busca top-k na base → trechos com citação."""

    def __init__(self, embeddings: EmbeddingsClient, chunk_repo=None) -> None:
        self.embeddings = embeddings
        self.chunk_repo = chunk_repo or DocumentChunkRepository()

    async def execute(self, query: str, top_k: int | None = None) -> list[KnowledgeSnippet]:
        vector = await self.embeddings.embed_query(query)
        return await self.chunk_repo.search_similar(vector, top_k=top_k)
```

- [ ] **Step 4: Ver passar**

Run: `pytest tests/unit/domain/documents/actions/test_search_knowledge_base_action.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/documents/actions/search_knowledge_base_action.py src/domain/documents/actions/__init__.py tests/unit/domain/documents/actions
git commit -m "feat(documents): SearchKnowledgeBaseAction (RAG clássico embed+search)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Tools HTTP do agente (`web_search`, `fetch_notion_page`) + formatação

**Files:**
- Create: `src/support/agent/tools.py`
- Test: `tests/unit/support/agent/test_tools.py`

**Interfaces:**
- Consumes: `TavilyClient`, `WebResult`, `NotionClient`, `Citation`.
- Produces:
  - `wrap_tool_content(text: str) -> str` — envolve em `<<TOOL_CONTENT>>…<</TOOL_CONTENT>>`.
  - `format_knowledge(snippets: list[KnowledgeSnippet]) -> str` — bloco de contexto rotulado por fonte.
  - `WebSearchTool(tavily, collected: list[Citation]).run(query: str) -> str` e `FetchNotionTool(notion).run(page_id: str) -> str` — retornam texto já em `<<TOOL_CONTENT>>`; `WebSearchTool` acrescenta as `Citation` das URLs em `collected`.

- [ ] **Step 1: Teste (unit) que falha**

`tests/unit/support/agent/test_tools.py`:

```python
import pytest

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from src.support.agent.tools import (
    WebSearchTool,
    format_knowledge,
    wrap_tool_content,
)
from tests.fakes.fake_tavily_client import FakeTavilyClient


def test_wrap_tool_content_uses_markers():
    out = wrap_tool_content("abc")
    assert out.startswith("<<TOOL_CONTENT>>") and out.endswith("<</TOOL_CONTENT>>")


def test_format_knowledge_labels_sources():
    snips = [KnowledgeSnippet("trecho", Citation("notion", "Regras", "u", "s", "pid"))]
    text = format_knowledge(snips)
    assert "Regras" in text and "trecho" in text
    assert text.startswith("<<TOOL_CONTENT>>")


@pytest.mark.asyncio
async def test_web_search_tool_collects_citations():
    from src.support.clients.tavily.tavily_client import WebResult

    collected: list[Citation] = []
    fake = FakeTavilyClient(results=[WebResult(title="Artigo", url="https://ex/a", content="corpo")])
    tool = WebSearchTool(tavily=fake, collected=collected)
    out = await tool.run("pergunta pública")
    assert out.startswith("<<TOOL_CONTENT>>")
    assert "Artigo" in out
    assert len(collected) == 1
    assert all(c.source_type == "web" for c in collected)
```

> `FakeTavilyClient()` retorna lista vazia por padrão — por isso o teste injeta um `WebResult` explícito.

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/support/agent/test_tools.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/support/agent/tools.py`:

```python
"""Ferramentas do oráculo. Conteúdo de fonte SEMPRE entre <<TOOL_CONTENT>> (dado
não-confiável). web_search e fetch_notion_page são HTTP (não tocam o banco), então
rodam com segurança durante o streaming."""

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from src.support.clients.notion.notion_client import NotionClient
from src.support.clients.tavily.tavily_client import TavilyClient

_OPEN = "<<TOOL_CONTENT>>"
_CLOSE = "<</TOOL_CONTENT>>"


def wrap_tool_content(text: str) -> str:
    return f"{_OPEN}\n{text}\n{_CLOSE}"


def format_knowledge(snippets: list[KnowledgeSnippet]) -> str:
    if not snippets:
        return wrap_tool_content("(nenhum trecho relevante na base de conhecimento)")
    blocks = [
        f"[Fonte: {s.citation.title} — {s.citation.url}]\n{s.content}" for s in snippets
    ]
    return wrap_tool_content("\n\n".join(blocks))


class WebSearchTool:
    def __init__(self, tavily: TavilyClient, collected: list[Citation]) -> None:
        self._tavily = tavily
        self._collected = collected

    async def run(self, query: str) -> str:
        results = await self._tavily.search(query)
        for r in results:
            self._collected.append(
                Citation(source_type="web", title=r.title, url=r.url, snippet=r.content[:200])
            )
        body = "\n\n".join(f"[{r.title} — {r.url}]\n{r.content}" for r in results)
        return wrap_tool_content(body or "(sem resultados na web)")


class FetchNotionTool:
    def __init__(self, notion: NotionClient) -> None:
        self._notion = notion

    async def run(self, page_id: str) -> str:
        page = await self._notion.get_page(page_id)
        return wrap_tool_content(f"[{page.title} — {page.url}]\n{page.content}")
```

- [ ] **Step 4: Ver passar**

Run: `pytest tests/unit/support/agent/test_tools.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/support/agent/tools.py tests/unit/support/agent/test_tools.py
git commit -m "feat(agent): tools web_search/fetch_notion + formatação TOOL_CONTENT

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: `OracleEngine` real (Pydantic AI) + `get_oracle_engine()`

**Files:**
- Create: `src/support/agent/oracle_engine.py`
- Test: `tests/unit/support/agent/test_oracle_engine.py`

**Interfaces:**
- Consumes: `SYSTEM_PROMPT`, `AgentMessage`, `AgentStreamChunk`, `KnowledgeSnippet`, `format_knowledge`, `WebSearchTool`, `FetchNotionTool`, `TavilyClient`, `NotionClient`, `Citation`.
- Produces:
  - `OracleEngine(model: ... | None = None).stream_answer(question, history, knowledge) -> AsyncIterator[AgentStreamChunk]`.
  - `get_oracle_engine() -> OracleEnginePort`.

> **Step 0 (verificação obrigatória de API):** antes de implementar, confirme a superfície instalada do Pydantic AI:
> `python -c "import pydantic_ai; print(pydantic_ai.__version__); from pydantic_ai import Agent; print([a for a in dir(Agent) if 'run' in a or 'tool' in a])"`
> O código abaixo usa `Agent(model, system_prompt=...)`, `@agent.tool_plain`, e `agent.run_stream(...)` com `result.stream_text(delta=True)`. Se a versão instalada divergir (nomes de método/streaming), **adapte a iteração do stream** mantendo o contrato: emitir `AgentStreamChunk(type="text", ...)` por delta e um `AgentStreamChunk(type="sources", ...)` no fim. Não altere o `OracleEnginePort`.

- [ ] **Step 1: Teste (unit) que falha**

Usa o `TestModel` do Pydantic AI (não chama LLM real). Se a API de teste divergir, ajuste conforme o Step 0.

`tests/unit/support/agent/test_oracle_engine.py`:

```python
import pytest

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.oracle_engine import OracleEngine
from src.support.agent.ports import AgentStreamChunk, KnowledgeSnippet


@pytest.mark.asyncio
async def test_engine_streams_text_and_final_sources():
    from pydantic_ai.models.test import TestModel  # modelo de teste do pydantic_ai

    engine = OracleEngine(model=TestModel())
    knowledge = [KnowledgeSnippet("o onboarding leva 7 dias", Citation("notion", "Onboarding", "u", "s", "pid"))]

    chunks = [c async for c in engine.stream_answer("quantos dias?", [], knowledge)]

    assert any(c.type == "text" for c in chunks)
    sources = [c for c in chunks if c.type == "sources"]
    assert len(sources) == 1
    # a citação da base injetada deve aparecer nas fontes finais
    assert any(cit.title == "Onboarding" for cit in sources[0].citations)
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/support/agent/test_oracle_engine.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/support/agent/oracle_engine.py`:

```python
"""Motor real do oráculo sobre Pydantic AI (ADR-0007). Único lugar que importa
pydantic_ai. RAG clássico (knowledge injetado) + tools HTTP agênticas."""

from typing import AsyncIterator

from pydantic_ai import Agent

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import AgentMessage, AgentStreamChunk, KnowledgeSnippet
from src.support.agent.prompts import SYSTEM_PROMPT
from src.support.agent.tools import FetchNotionTool, WebSearchTool, format_knowledge
from src.support.clients.notion.notion_client import NotionClient
from src.support.clients.tavily.tavily_client import TavilyClient
from src.support.core.settings import settings


def _model_id() -> str:
    if settings.LLM_PROVIDER == "openai":
        return f"openai:{settings.OPENAI_MODEL}"
    return f"anthropic:{settings.ANTHROPIC_MODEL}"


def _build_prompt(question: str, history: list[AgentMessage], knowledge: list[KnowledgeSnippet]) -> str:
    parts: list[str] = []
    for msg in history:
        parts.append(f"{msg.role}: {msg.content}")
    parts.append("Contexto recuperado da base de conhecimento:")
    parts.append(format_knowledge(knowledge))
    parts.append(f"Pergunta do usuário: {question}")
    return "\n\n".join(parts)


class OracleEngine:
    def __init__(self, model=None) -> None:
        self._model = model or _model_id()

    async def stream_answer(
        self,
        question: str,
        history: list[AgentMessage],
        knowledge: list[KnowledgeSnippet],
    ) -> AsyncIterator[AgentStreamChunk]:
        web_citations: list[Citation] = []
        web_tool = WebSearchTool(tavily=TavilyClient(), collected=web_citations)
        notion_tool = FetchNotionTool(notion=NotionClient())

        agent = Agent(self._model, system_prompt=SYSTEM_PROMPT)

        @agent.tool_plain
        async def web_search(query: str) -> str:
            """Busca informação pública na web quando a base interna não cobre."""
            return await web_tool.run(query)

        @agent.tool_plain
        async def fetch_notion_page(page_id: str) -> str:
            """Busca o conteúdo completo/atualizado de uma página do Notion."""
            return await notion_tool.run(page_id)

        prompt = _build_prompt(question, history, knowledge)
        async with agent.run_stream(prompt) as result:
            async for delta in result.stream_text(delta=True):
                yield AgentStreamChunk(type="text", text=delta)

        kb_citations = [s.citation for s in knowledge]
        yield AgentStreamChunk(type="sources", citations=kb_citations + web_citations)


def get_oracle_engine() -> "OracleEngine":
    return OracleEngine()
```

- [ ] **Step 4: Ver passar**

Run: `pytest tests/unit/support/agent/test_oracle_engine.py -v`
Expected: PASS. (Se `TestModel`/`stream_text` divergirem na versão instalada, aplique o ajuste do Step 0.)

- [ ] **Step 5: Commit**

```bash
git add src/support/agent/oracle_engine.py tests/unit/support/agent/test_oracle_engine.py
git commit -m "feat(agent): OracleEngine real (Pydantic AI) + get_oracle_engine

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: `AnswerQuestionAction` (compõe RAG + engine)

**Files:**
- Create: `src/domain/conversations/actions/answer_question_action.py`
- Modify: `src/domain/conversations/actions/__init__.py`
- Test: `tests/unit/domain/conversations/actions/test_answer_question_action.py`

**Interfaces:**
- Consumes: `OracleEnginePort`, `SearchKnowledgeBaseAction`, `AgentMessage`, `AgentStreamChunk`.
- Produces: `AnswerQuestionAction(engine: OracleEnginePort, search: SearchKnowledgeBaseAction).execute(question: str, history: list[AgentMessage]) -> AsyncIterator[AgentStreamChunk]`.

> A recuperação (`search.execute`) é **awaited dentro de `execute`** (sessão viva), e só então o iterador do engine é retornado — garantindo que nenhum acesso a DB ocorra durante o streaming.

- [ ] **Step 1: Teste (unit) que falha**

`tests/unit/domain/conversations/actions/test_answer_question_action.py`:

```python
import pytest

from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from tests.fakes.fake_oracle_engine import FakeOracleEngine


class _FakeSearch:
    def __init__(self, snippets):
        self.snippets = snippets
        self.called_with = None

    async def execute(self, query, top_k=None):
        self.called_with = query
        return self.snippets


@pytest.mark.asyncio
async def test_answer_retrieves_then_streams():
    snippets = [KnowledgeSnippet("ctx", Citation("notion", "Onboarding", "u", "s", "pid"))]
    search = _FakeSearch(snippets)
    action = AnswerQuestionAction(engine=FakeOracleEngine(answer="resposta final"), search=search)

    chunks = [c async for c in await action.execute("pergunta?", [])]

    assert search.called_with == "pergunta?"
    assert any(c.type == "text" for c in chunks)
    sources = [c for c in chunks if c.type == "sources"][0]
    assert any(cit.title == "Onboarding" for cit in sources.citations)
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/unit/domain/conversations/actions/test_answer_question_action.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar**

`src/domain/conversations/actions/answer_question_action.py`:

```python
from typing import AsyncIterator

from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.ports import AgentMessage, AgentStreamChunk, OracleEnginePort


class AnswerQuestionAction:
    """Caso de uso do oráculo: recupera a base (RAG clássico) e delega o streaming
    ao motor. Composição de Action (SearchKnowledgeBaseAction) + engine."""

    def __init__(self, engine: OracleEnginePort, search: SearchKnowledgeBaseAction) -> None:
        self.engine = engine
        self.search = search

    async def execute(
        self, question: str, history: list[AgentMessage]
    ) -> AsyncIterator[AgentStreamChunk]:
        knowledge = await self.search.execute(question)  # sessão viva aqui
        return self.engine.stream_answer(question, history, knowledge)
```

- [ ] **Step 4: Ver passar**

Run: `pytest tests/unit/domain/conversations/actions/test_answer_question_action.py -v`
Expected: PASS. (Crie os `__init__.py` de teste que faltarem.)

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/actions tests/unit/domain/conversations/actions
git commit -m "feat(conversations): AnswerQuestionAction (RAG clássico + engine streaming)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: API — request schema + controller + rota SSE

**Files:**
- Create: `src/app/api/requests/ask_question_request.py`
- Create: `src/app/api/controllers/conversation_controller.py`
- Create: `src/app/api/routes/conversations.py`
- Test: `tests/integration/api/test_ask_endpoint.py`

**Interfaces:**
- Consumes: `AnswerQuestionAction`, `SearchKnowledgeBaseAction`, `get_oracle_engine`, `get_embeddings_client`, `AgentMessage`, `AgentStreamChunk`.
- Produces:
  - `AskQuestionRequest { question: str, history: list[MessageIn] }` (`MessageIn { role: str, content: str }`).
  - `ConversationController.ask(request, data) -> StreamingResponse` (`text/event-stream`).
  - Rota `POST /conversations/ask` via `public_router`.

- [ ] **Step 1: Teste (integração) que falha**

Injetamos um engine fake sobrescrevendo `get_oracle_engine` para não chamar LLM. Usa a base já semeada (ou tolera base vazia).

`tests/integration/api/test_ask_endpoint.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_ask_streams_sse(monkeypatch):
    import src.app.api.controllers.conversation_controller as ctrl
    from tests.fakes.fake_oracle_engine import FakeOracleEngine

    monkeypatch.setattr(ctrl, "get_oracle_engine", lambda: FakeOracleEngine(answer="resposta de teste"))

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversations/ask",
            json={"question": "o que é o onboarding?", "history": []},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "resposta" in body
        assert "sources" in body  # evento final de fontes
```

> Requer Postgres+pgvector rodando e o banco de dev migrado (o endpoint faz retrieval real via `SearchKnowledgeBaseAction`, que embeda a query — configure `OPENAI_API_KEY` de teste ou faça o monkeypatch de `get_embeddings_client` no controller para `FakeEmbeddingsClient` se quiser isolar de rede).

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/integration/api/test_ask_endpoint.py -v`
Expected: FAIL (404 / ImportError).

- [ ] **Step 3: Implementar request schema**

`src/app/api/requests/ask_question_request.py`:

```python
from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[MessageIn] = Field(default_factory=list)
```

- [ ] **Step 4: Implementar controller**

`src/app/api/controllers/conversation_controller.py`:

```python
import json
from typing import AsyncIterator

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.app.api.requests.ask_question_request import AskQuestionRequest
from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.oracle_engine import get_oracle_engine
from src.support.agent.ports import AgentMessage
from src.support.clients.embeddings.embeddings_client import get_embeddings_client


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ConversationController:
    @staticmethod
    async def ask(request: Request, data: AskQuestionRequest) -> StreamingResponse:
        history = [AgentMessage(role=m.role, content=m.content) for m in data.history]
        search = SearchKnowledgeBaseAction(embeddings=get_embeddings_client())
        action = AnswerQuestionAction(engine=get_oracle_engine(), search=search)

        # retrieval acontece aqui (sessão viva); stream só faz HTTP depois
        stream = await action.execute(data.question, history)

        async def event_source() -> AsyncIterator[str]:
            async for chunk in stream:
                if chunk.type == "text":
                    yield _sse("token", {"text": chunk.text})
                elif chunk.type == "sources":
                    yield _sse(
                        "sources",
                        {
                            "citations": [
                                {
                                    "source_type": c.source_type,
                                    "title": c.title,
                                    "url": c.url,
                                    "snippet": c.snippet,
                                }
                                for c in chunk.citations
                            ]
                        },
                    )
            yield _sse("done", {})

        return StreamingResponse(event_source(), media_type="text/event-stream")
```

- [ ] **Step 5: Implementar rota**

`src/app/api/routes/conversations.py`:

```python
"""Rota do oráculo — pública no nível da app (protegida por Cloudflare Access na borda)."""

from fastapi import APIRouter

from src.app.api.controllers.conversation_controller import ConversationController

public_router = APIRouter(prefix="/conversations", tags=["Conversations"])
public_router.post("/ask")(ConversationController.ask)
```

- [ ] **Step 6: Ver passar**

Run: `pytest tests/integration/api/test_ask_endpoint.py -v`
Expected: PASS. (Crie `tests/integration/api/__init__.py` se necessário.)

- [ ] **Step 7: Commit**

```bash
git add src/app/api/requests/ask_question_request.py src/app/api/controllers/conversation_controller.py src/app/api/routes/conversations.py tests/integration/api
git commit -m "feat(api): endpoint POST /conversations/ask com streaming SSE

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: UI web mínima de chat

**Files:**
- Create: `src/app/web/index.html`
- Create: `src/app/api/routes/web.py`
- Test: `tests/integration/api/test_web_ui.py`

**Interfaces:**
- Produces: rota `GET /` que serve `src/app/web/index.html`; a página consome `POST /conversations/ask` via `fetch` + leitura incremental do stream.

- [ ] **Step 1: Teste (integração) que falha**

`tests/integration/api/test_web_ui.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_root_serves_chat_page():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Oracle Borderless" in resp.text
```

- [ ] **Step 2: Ver falhar**

Run: `pytest tests/integration/api/test_web_ui.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Criar a página**

`src/app/web/index.html`:

```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Oracle Borderless</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    #answer { white-space: pre-wrap; border: 1px solid #ddd; border-radius: 8px; padding: 1rem; min-height: 4rem; }
    #sources { margin-top: 1rem; font-size: .9rem; color: #555; }
    input, button { font-size: 1rem; padding: .5rem; }
    #q { width: 100%; box-sizing: border-box; margin-bottom: .5rem; }
  </style>
</head>
<body>
  <h1>Oracle Borderless</h1>
  <input id="q" placeholder="Faça sua pergunta..." />
  <button id="send">Perguntar</button>
  <h3>Resposta</h3>
  <div id="answer"></div>
  <div id="sources"></div>
  <script>
    const answerEl = document.getElementById("answer");
    const sourcesEl = document.getElementById("sources");
    document.getElementById("send").onclick = async () => {
      answerEl.textContent = "";
      sourcesEl.innerHTML = "";
      const question = document.getElementById("q").value;
      const resp = await fetch("/conversations/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history: [] }),
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop();
        for (const evt of events) {
          const lines = evt.split("\n");
          const type = (lines.find(l => l.startsWith("event:")) || "").slice(6).trim();
          const dataLine = lines.find(l => l.startsWith("data:"));
          if (!dataLine) continue;
          const data = JSON.parse(dataLine.slice(5).trim());
          if (type === "token") answerEl.textContent += data.text;
          if (type === "sources") {
            sourcesEl.innerHTML = "<strong>Fontes:</strong><br>" +
              data.citations.map(c => `• <a href="${c.url}">${c.title}</a> (${c.source_type})`).join("<br>");
          }
        }
      }
    };
  </script>
</body>
</html>
```

- [ ] **Step 4: Servir a página**

`src/app/api/routes/web.py`:

```python
"""Serve a UI web mínima do oráculo. Pública (protegida por Cloudflare Access na borda)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

public_router = APIRouter(tags=["Web"])
_INDEX = Path(__file__).resolve().parents[2] / "web" / "index.html"


@public_router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(_INDEX.read_text(encoding="utf-8"))
```

> Confirme que `parents[2]` resolve para `src/app/` a partir de `src/app/api/routes/web.py` (routes → api → app). Ajuste o índice se a estrutura divergir.

- [ ] **Step 5: Ver passar**

Run: `pytest tests/integration/api/test_web_ui.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/app/web/index.html src/app/api/routes/web.py tests/integration/api/test_web_ui.py
git commit -m "feat(web): UI mínima de chat consumindo o stream SSE

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: `.env.example` + notas de deploy (Cloudflare Access)

**Files:**
- Create: `.env.example`
- Modify: `docker/README.md` (ou criar) — nota de deploy CF Access.

**Interfaces:** nenhuma (documentação/config).

- [ ] **Step 1: Criar `.env.example`**

`.env.example`:

```dotenv
# --- Ambiente ---
ENVIRONMENT=development
DEBUG=true
ENABLE_SCHEDULER=true

# --- Banco (defaults do docker-compose) ---
DB_HOST=localhost
DB_PORT=5432
DB_USER=oracle
DB_PASSWORD=oracle
DB_NAME=oracle_borderless
DB_NAME_TEST=oracle_borderless_test

# --- LLM do oráculo ---
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=            # preencher
ANTHROPIC_MODEL=claude-opus-4-8
# OPENAI_MODEL=gpt-4o         # se LLM_PROVIDER=openai

# --- Embeddings (OpenAI; necessário mesmo usando Claude no chat) ---
OPENAI_API_KEY=               # preencher

# --- Base de conhecimento: Notion via MCP (token JÁ disponível; preencher no final) ---
NOTION_MCP_URL=               # preencher
NOTION_MCP_TOKEN=             # preencher

# --- Web search ---
TAVILY_API_KEY=               # preencher

# --- RAG ---
RAG_TOP_K=6
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=200
```

- [ ] **Step 2: Nota de deploy (Cloudflare Access)**

Adicione a `docker/README.md` (crie se não existir):

```markdown
## Autenticação — Cloudflare Access (edge)

A app NÃO implementa auth. O acesso é restrito por **Cloudflare Access** na frente
da aplicação:

1. Configure um túnel/hostname público apontando para o serviço FastAPI.
2. Crie uma aplicação em Cloudflare Access cobrindo esse hostname.
3. Defina a política (e-mails/grupos com acesso ao ecossistema).

O Cloudflare injeta `Cf-Access-Jwt-Assertion` e `Cf-Access-Authenticated-User-Email`.
Validar esse JWT numa dependency do FastAPI é trabalho FUTURO (fora do M1).
```

- [ ] **Step 3: Commit**

```bash
git add .env.example docker/README.md
git commit -m "docs(config): .env.example + nota de deploy Cloudflare Access

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Verificação final do Milestone

- [ ] `pytest` (suíte completa) — unit passa sem DB; integração passa com Postgres+pgvector rodando.
- [ ] `python -c "from main import app; print('OK')"` — app importa.
- [ ] `alembic check` — sem migrations pendentes.
- [ ] `prospector` — lint limpo.
- [ ] Smoke manual: `uvicorn main:app --reload`, seed dev (`python -m database.seeds`), abrir `http://localhost:8000/`, perguntar e ver resposta em streaming com fontes.

---

## Self-Review (cobertura do spec)

- Infra pgvector (spec §2) → Task 4. ✅
- Entities/Models/Mappers/Repos (spec §3) → Tasks 2, 3, 5, 6. ✅
- Ingestão source-agnostic + Notion + seed (spec §4) → Tasks 7, 8, 9. ✅
- Tools (spec §5) → `web_search`/`fetch_notion_page` na Task 11; `search_knowledge_base` virou RAG clássico (Task 10) por decisão de sessão/streaming. ✅
- OracleEngine Pydantic AI (spec §6) → Task 12. ✅
- AnswerQuestionAction + API + UI (spec §7) → Tasks 13, 14, 15. ✅
- Guardrails (spec §8) → prompt já existente + `wrap_tool_content` (Task 11). ✅
- Cloudflare Access (spec §9) → Task 16 (endpoint público + nota deploy). ✅
- `.env` placeholders (spec §10) → Task 16. ✅
- Testes (spec §11) → embutidos em cada task. ✅
- Custo/qualidade (spec §12) → embeddings small, top_k=6, web_search sob demanda; modelo caro registrado como alavanca. ✅

**Desvio consciente vs. spec:** a base de conhecimento é recuperada por **RAG clássico** (não como tool agêntica), decidido para respeitar a regra 3 no streaming SSE. `web_search` e `fetch_notion_page` seguem agênticas. Tornar a base totalmente agêntica é trabalho futuro (exigiria ADR sobre ciclo de vida de sessão em streaming).

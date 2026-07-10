# Milestone 2 — Memória Episódica — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar memória de conversa ao oráculo — persistir os turnos em Postgres, tornar o servidor a fonte da verdade (`conversation_id`), carregar recência por orçamento de tokens na working memory, e permitir listar/reabrir conversas antigas.

**Architecture:** Novo conteúdo no subdomínio `src/domain/conversations/` (Entity ≠ Model + Mapper + Repository, ADR-0003). O `AnswerQuestionAction` passa a criar/reusar a conversa e gravar a mensagem do usuário **dentro do escopo do request** (sessão viva); a resposta do oráculo é acumulada durante o streaming SSE e persistida **no fim do gerador, com uma sessão própria** (mesmo padrão de Job/Command/Seed) — porque durante o corpo SSE não há sessão de request. Endpoints e UI mínima ganham a superfície de retomar conversas.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async (`asyncpg`), Alembic, Pydantic v2, Postgres 16 + pgvector (JSONB nativo), pytest/pytest-asyncio. UV como package manager.

## Global Constraints

- **Domain não importa infra HTTP.** Entities em `src/domain/conversations/entities/` são dataclasses puras — sem `sqlalchemy`, `fastapi`, `pydantic`. *(regra 1 / ADR-0003)*
- **Entity ≠ Model; conversão só no Mapper** (`src/domain/conversations/mappers/`), nunca inline no Repository. *(regra 2 / ADR-0003)*
- **Sessão vem do contexto** via `CurrentAsyncSessionContext.get()`; repositórios nunca criam sessão. A única exceção é trabalho fora do request (persistência pós-stream), que usa o helper `run_in_async_session` — o mesmo padrão de `Job.execute()`. *(regra 3 / ADR-0006)*
- **Controllers finos:** recebem request, chamam Actions, retornam Response. Sem regra de negócio. *(regra 5)*
- **Sem Service agregador.** Cada caso de uso é uma Action; composição = Action chamando Action. Domain Service só para regra sem dono (usamos um: `ConversationAccessPolicy`). *(regra 6)*
- **Schemas Pydantic ficam em `src/app/api/`.** DTOs internos são dataclasses no domínio. *(regra 7)*
- **PK padrão UUID v7** via `uuid6.uuid7()` ao construir entities novas (não `uuid4`). *(convenção do projeto)*
- **Sem dependências novas.** A contagem de tokens é heurística (`len(texto)//4`); nada de `tiktoken`. *(regra 10)*
- **`user_email` é best-effort e não validado** — lido do header `Cf-Access-Authenticated-User-Email`, nullable. Nada de validação de JWT neste milestone.

**Pré-condições de ambiente (para rodar os testes de integração):** Postgres pgvector no ar e as duas bases migradas, conforme M1 §2. Se a porta `5432` estiver ocupada por outro projeto, suba o pgvector em outra porta e exporte `DB_PORT` (ex.: `DB_PORT=5434`) antes de `alembic upgrade head` e `pytest`. Aplicar migrations nas duas bases: base principal e `oracle_borderless_test`.

---

### Task 1: Settings de recência + helper de sessão própria

**Files:**
- Modify: `src/support/core/settings.py` (adicionar duas settings no bloco RAG/memória)
- Create: `src/support/core/session_scope.py`
- Test: `tests/unit/support/test_session_scope.py`

**Interfaces:**
- Produces:
  - `settings.MEMORY_RECENCY_TOKEN_BUDGET: int` (default `2000`), `settings.MEMORY_RECENCY_MAX_MESSAGES: int` (default `50`).
  - `async def run_in_async_session(fn: Callable[[], Awaitable[T]]) -> T` — abre `AsyncSessionLocal`, popula `CurrentAsyncSessionContext`, roda `fn()`, comita (rollback em erro), limpa o contexto.

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/unit/support/test_session_scope.py
import pytest

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.session_scope import run_in_async_session


@pytest.mark.asyncio
async def test_run_in_async_session_populates_and_clears_context(monkeypatch):
    seen = {}

    class FakeSession:
        async def commit(self): seen["committed"] = True
        async def rollback(self): seen["rolledback"] = True
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("src.support.core.session_scope.AsyncSessionLocal", lambda: FakeSession())

    async def work():
        assert CurrentAsyncSessionContext.get() is not None  # sessão viva durante fn
        return "ok"

    result = await run_in_async_session(work)

    assert result == "ok"
    assert seen.get("committed") is True
    assert CurrentAsyncSessionContext.get() is None  # limpo ao final
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/unit/support/test_session_scope.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.support.core.session_scope'`

- [ ] **Step 3: Implementar o helper**

```python
# src/support/core/session_scope.py
"""Executa uma coroutine num escopo de sessão async própria — para trabalho fora
do ciclo de request (ex.: persistir a resposta do oráculo depois que o streaming
SSE termina, quando a sessão do request já foi comitada e limpa).

Mesma mecânica de Job.execute()/Commands/Seeds: abre AsyncSessionLocal, popula o
contexto, comita, limpa. Os repositórios continuam lendo a sessão via
CurrentAsyncSessionContext.get() — sem criar sessão eles próprios (regra 3)."""

from typing import Awaitable, Callable, TypeVar

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal

T = TypeVar("T")


async def run_in_async_session(fn: Callable[[], Awaitable[T]]) -> T:
    async with AsyncSessionLocal() as session:
        CurrentAsyncSessionContext.set(session)
        try:
            result = await fn()
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            CurrentAsyncSessionContext.clear()
```

- [ ] **Step 4: Adicionar as settings**

Em `src/support/core/settings.py`, logo após a linha `RAG_CHUNK_OVERLAP: int = 200`, adicione:

```python
    # Memória episódica (M2) — recência carregada na working memory
    MEMORY_RECENCY_TOKEN_BUDGET: int = 2000
    MEMORY_RECENCY_MAX_MESSAGES: int = 50
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/unit/support/test_session_scope.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/support/core/session_scope.py src/support/core/settings.py tests/unit/support/test_session_scope.py
git commit -m "feat(support): helper run_in_async_session + settings de recência (M2)"
```

---

### Task 2: Entities, Models e Migration das tabelas de conversa

**Files:**
- Create: `src/domain/conversations/entities/conversation.py`
- Create: `src/domain/conversations/entities/message.py`
- Create: `src/domain/conversations/models/conversation.py`
- Create: `src/domain/conversations/models/message.py`
- Create: `database/migrations/versions/0002_conversations.py`
- Test: `tests/integration/test_migration_conversations.py`

**Interfaces:**
- Produces:
  - Entity `Conversation(uuid: UUID, user_email: str | None, title: str | None, created_at: datetime, updated_at: datetime, deleted_at: datetime | None)`.
  - Entity `Message(uuid: UUID, conversation_id: UUID, role: str, content: str, sources: list[Citation] | None, created_at: datetime)`.
  - `ConversationModel` (tabela `conversations`), `MessageModel` (tabela `messages`, coluna `sources` JSONB, índice `(conversation_id, created_at)`).
  - Migration revision `0002_conversations` (down_revision `0001_documents_pgvector`).

- [ ] **Step 1: Escrever o teste falho (migration cria as tabelas)**

```python
# tests/integration/test_migration_conversations.py
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_conversation_tables_exist(db_session):
    for table in ("conversations", "messages"):
        r = await db_session.execute(text("SELECT to_regclass(:t)"), {"t": table})
        assert r.scalar_one() is not None
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `DB_PORT=${DB_PORT:-5432} python -m pytest tests/integration/test_migration_conversations.py -v`
Expected: FAIL — `assert None is not None` (tabelas ainda não existem)

- [ ] **Step 3: Criar as Entities (dataclasses puras)**

```python
# src/domain/conversations/entities/conversation.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Conversation:
    """Entidade de domínio de uma conversa. Pura — sem SQLAlchemy."""

    uuid: UUID
    user_email: str | None
    title: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
```

```python
# src/domain/conversations/entities/message.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.shared.value_objects.citation import Citation


@dataclass
class Message:
    """Um turno da conversa. `sources` só é preenchido em mensagens do assistente."""

    uuid: UUID
    conversation_id: UUID
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime
    sources: list[Citation] | None = None
```

- [ ] **Step 4: Criar os Models (SQLAlchemy)**

```python
# src/domain/conversations/models/conversation.py
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import ApplyRelations, HasTimestamps, HasUUID
from src.support.core.models.base_model import BaseModel


class ConversationModel(BaseModel, HasUUID, HasTimestamps, ApplyRelations):
    __tablename__ = "conversations"

    user_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

```python
# src/domain/conversations/models/message.py
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import HasUUID
from src.support.core.models.base_model import BaseModel


class MessageModel(BaseModel, HasUUID):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.uuid", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)
```

- [ ] **Step 5: Criar a migration**

```python
# database/migrations/versions/0002_conversations.py
"""conversations + messages (memória episódica)

Revision ID: 0002_conversations
Revises: 0001_documents_pgvector
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_conversations"
down_revision = "0001_documents_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column("user_email", sa.String(320), nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_conversations_user_email", "conversations", ["user_email"])

    op.create_table(
        "messages",
        sa.Column("uuid", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user_email", table_name="conversations")
    op.drop_table("conversations")
```

- [ ] **Step 6: Aplicar a migration nas duas bases e rodar o teste**

```bash
alembic upgrade head
DB_NAME=oracle_borderless_test alembic upgrade head
python -m pytest tests/integration/test_migration_conversations.py -v
```
Expected: PASS. (Se a porta 5432 estiver ocupada, prefixe os comandos com `DB_PORT=5434`.)

- [ ] **Step 7: Confirmar consistência do metadata do Alembic**

Run: `alembic check`
Expected: "No new upgrade operations detected." (os Models são autodescobertos por `database/env.py`; nenhuma diferença deve sobrar)

- [ ] **Step 8: Commit**

```bash
git add src/domain/conversations/entities src/domain/conversations/models database/migrations/versions/0002_conversations.py tests/integration/test_migration_conversations.py
git commit -m "feat(conversations): entities, models e migration de conversa+mensagens (M2)"
```

---

### Task 3: Mappers (roundtrip, incl. serialização de `sources`)

**Files:**
- Create: `src/domain/conversations/mappers/conversation_mapper.py`
- Create: `src/domain/conversations/mappers/message_mapper.py`
- Create: `src/domain/conversations/mappers/__init__.py`
- Test: `tests/unit/domain/conversations/mappers/test_mappers.py`

**Interfaces:**
- Consumes: `Conversation`, `Message` (Task 2); `ConversationModel`, `MessageModel` (Task 2); `Citation`.
- Produces:
  - `ConversationMapper.to_entity(model) -> Conversation`, `ConversationMapper.to_model_attrs(entity) -> dict`.
  - `MessageMapper.to_entity(model) -> Message`, `MessageMapper.to_model_attrs(entity) -> dict` (serializa/desserializa `sources` como lista de dicts JSONB).

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/unit/domain/conversations/mappers/test_mappers.py
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.conversations.entities.message import Message
from src.domain.conversations.mappers import MessageMapper
from src.domain.shared.value_objects.citation import Citation


def test_message_to_model_attrs_serializes_sources():
    cid, mid = uuid4(), uuid4()
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    msg = Message(
        uuid=mid, conversation_id=cid, role="assistant", content="oi",
        created_at=now,
        sources=[Citation("notion", "Doc", "https://n", "trecho", "pid-1")],
    )
    attrs = MessageMapper.to_model_attrs(msg)
    assert attrs["role"] == "assistant"
    assert attrs["sources"] == [
        {"source_type": "notion", "title": "Doc", "url": "https://n", "snippet": "trecho", "page_id": "pid-1"}
    ]
    assert "created_at" not in attrs  # timestamp é server default


def test_message_to_model_attrs_none_sources():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    msg = Message(uuid=uuid4(), conversation_id=uuid4(), role="user", content="q", created_at=now)
    assert MessageMapper.to_model_attrs(msg)["sources"] is None


def test_message_to_entity_deserializes_sources():
    class FakeModel:
        uuid = uuid4(); conversation_id = uuid4(); role = "assistant"; content = "oi"
        created_at = datetime(2026, 7, 10, tzinfo=timezone.utc)
        sources = [{"source_type": "web", "title": "T", "url": "https://x", "snippet": "s", "page_id": None}]

    entity = MessageMapper.to_entity(FakeModel())
    assert entity.sources[0] == Citation("web", "T", "https://x", "s", None)
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/unit/domain/conversations/mappers/test_mappers.py -v`
Expected: FAIL — `ModuleNotFoundError: ... conversations.mappers`

- [ ] **Step 3: Implementar os mappers**

```python
# src/domain/conversations/mappers/conversation_mapper.py
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.models.conversation import ConversationModel


class ConversationMapper:
    @staticmethod
    def to_entity(model: ConversationModel) -> Conversation:
        return Conversation(
            uuid=model.uuid,
            user_email=model.user_email,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model_attrs(entity: Conversation) -> dict:
        return {
            "uuid": entity.uuid,
            "user_email": entity.user_email,
            "title": entity.title,
            "deleted_at": entity.deleted_at,
        }
```

```python
# src/domain/conversations/mappers/message_mapper.py
from src.domain.conversations.entities.message import Message
from src.domain.conversations.models.message import MessageModel
from src.domain.shared.value_objects.citation import Citation


class MessageMapper:
    @staticmethod
    def _citation_to_dict(c: Citation) -> dict:
        return {
            "source_type": c.source_type,
            "title": c.title,
            "url": c.url,
            "snippet": c.snippet,
            "page_id": c.page_id,
        }

    @staticmethod
    def _dict_to_citation(d: dict) -> Citation:
        return Citation(
            source_type=d["source_type"],
            title=d["title"],
            url=d["url"],
            snippet=d["snippet"],
            page_id=d.get("page_id"),
        )

    @staticmethod
    def to_entity(model: MessageModel) -> Message:
        sources = (
            [MessageMapper._dict_to_citation(d) for d in model.sources]
            if model.sources
            else None
        )
        return Message(
            uuid=model.uuid,
            conversation_id=model.conversation_id,
            role=model.role,
            content=model.content,
            created_at=model.created_at,
            sources=sources,
        )

    @staticmethod
    def to_model_attrs(entity: Message) -> dict:
        sources = (
            [MessageMapper._citation_to_dict(c) for c in entity.sources]
            if entity.sources
            else None
        )
        return {
            "uuid": entity.uuid,
            "conversation_id": entity.conversation_id,
            "role": entity.role,
            "content": entity.content,
            "sources": sources,
        }
```

```python
# src/domain/conversations/mappers/__init__.py
from src.domain.conversations.mappers.conversation_mapper import ConversationMapper
from src.domain.conversations.mappers.message_mapper import MessageMapper

__all__ = ["ConversationMapper", "MessageMapper"]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/unit/domain/conversations/mappers/test_mappers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/mappers tests/unit/domain/conversations/mappers
git commit -m "feat(conversations): mappers com serialização de citações em JSONB (M2)"
```

---

### Task 4: ConversationRepository

**Files:**
- Create: `src/domain/conversations/repositories/conversation_repository.py`
- Test: `tests/integration/domain/conversations/test_conversation_repository.py`

**Interfaces:**
- Consumes: `Conversation`, `ConversationModel`, `ConversationMapper`, `CurrentAsyncSessionContext`.
- Produces:
  - `ConversationRepository().get_by_id(uuid) -> Conversation | None`
  - `ConversationRepository().create(conversation: Conversation) -> Conversation`
  - `ConversationRepository().list_by_user(user_email: str | None) -> list[Conversation]` (ordena por `updated_at desc`, exclui `deleted_at`; `user_email=None` retorna as sem dono)

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/integration/domain/conversations/test_conversation_repository.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository


def _conv(user_email=None, title="T"):
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    return Conversation(uuid4(), user_email, title, now, now, None)


@pytest.mark.asyncio
async def test_create_then_get_by_id(db_session):
    repo = ConversationRepository()
    created = await repo.create(_conv(user_email="a@x.com", title="Primeira"))
    await db_session.flush()

    found = await repo.get_by_id(created.uuid)
    assert found is not None
    assert found.title == "Primeira"
    assert found.user_email == "a@x.com"


@pytest.mark.asyncio
async def test_list_by_user_filters_and_orders(db_session):
    repo = ConversationRepository()
    await repo.create(_conv(user_email="a@x.com", title="A1"))
    await repo.create(_conv(user_email="b@x.com", title="B1"))
    await db_session.flush()

    mine = await repo.list_by_user("a@x.com")
    assert [c.title for c in mine] == ["A1"]


@pytest.mark.asyncio
async def test_list_by_user_none_returns_ownerless(db_session):
    repo = ConversationRepository()
    await repo.create(_conv(user_email=None, title="Anon"))
    await repo.create(_conv(user_email="a@x.com", title="Owned"))
    await db_session.flush()

    anon = await repo.list_by_user(None)
    assert all(c.user_email is None for c in anon)
    assert "Anon" in [c.title for c in anon]
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/domain/conversations/test_conversation_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: ... conversation_repository`

- [ ] **Step 3: Implementar o repository**

```python
# src/domain/conversations/repositories/conversation_repository.py
from uuid import UUID

from sqlalchemy import select

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.mappers import ConversationMapper
from src.domain.conversations.models.conversation import ConversationModel
from src.support.core.context import CurrentAsyncSessionContext


class ConversationRepository:
    def __init__(self) -> None:
        self.session = CurrentAsyncSessionContext.get()

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(ConversationModel).where(ConversationModel.uuid == conversation_id)
        )
        model = result.scalar_one_or_none()
        return ConversationMapper.to_entity(model) if model else None

    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(**ConversationMapper.to_model_attrs(conversation))
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return ConversationMapper.to_entity(model)

    async def list_by_user(self, user_email: str | None) -> list[Conversation]:
        stmt = select(ConversationModel).where(ConversationModel.deleted_at.is_(None))
        if user_email is None:
            stmt = stmt.where(ConversationModel.user_email.is_(None))
        else:
            stmt = stmt.where(ConversationModel.user_email == user_email)
        stmt = stmt.order_by(ConversationModel.updated_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [ConversationMapper.to_entity(m) for m in rows]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/domain/conversations/test_conversation_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/repositories/conversation_repository.py tests/integration/domain/conversations/test_conversation_repository.py
git commit -m "feat(conversations): ConversationRepository (get/create/list_by_user)"
```

---

### Task 5: MessageRepository (append + load_recent + list)

**Files:**
- Create: `src/domain/conversations/repositories/message_repository.py`
- Test: `tests/integration/domain/conversations/test_message_repository.py`

**Interfaces:**
- Consumes: `Message`, `MessageModel`, `MessageMapper`, `ConversationModel`, `AgentMessage` (`src/support/agent/ports.py`), `settings`.
- Produces:
  - `MessageRepository().append(message: Message) -> Message` (grava o turno **e** bumpa `conversations.updated_at`)
  - `MessageRepository().load_recent(conversation_id: UUID) -> list[AgentMessage]` (mais recentes até `MEMORY_RECENCY_TOKEN_BUDGET`, ordem cronológica final; ≥1 mensagem sempre)
  - `MessageRepository().list_by_conversation(conversation_id: UUID) -> list[Message]` (ordem cronológica)

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/integration/domain/conversations/test_message_repository.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.repositories.message_repository import MessageRepository


async def _new_conversation(db_session) -> "Conversation":
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    conv = await ConversationRepository().create(
        Conversation(uuid4(), None, "T", now, now, None)
    )
    await db_session.flush()
    return conv


def _msg(conversation_id, role, content):
    return Message(uuid4(), conversation_id, role, content, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_append_and_list_chronological(db_session):
    conv = await _new_conversation(db_session)
    repo = MessageRepository()
    await repo.append(_msg(conv.uuid, "user", "pergunta 1"))
    await repo.append(_msg(conv.uuid, "assistant", "resposta 1"))
    await db_session.flush()

    msgs = await repo.list_by_conversation(conv.uuid)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert [m.content for m in msgs] == ["pergunta 1", "resposta 1"]


@pytest.mark.asyncio
async def test_load_recent_respects_token_budget(db_session, monkeypatch):
    # Budget minúsculo: cada mensagem de 40 chars ~= 10 tokens (len//4).
    monkeypatch.setattr("src.domain.conversations.repositories.message_repository.settings.MEMORY_RECENCY_TOKEN_BUDGET", 15)
    conv = await _new_conversation(db_session)
    repo = MessageRepository()
    for i in range(5):
        await repo.append(_msg(conv.uuid, "user", "x" * 40))  # ~10 tokens cada
        await db_session.flush()

    recent = await repo.load_recent(conv.uuid)
    # 15 de budget: cabe a última (10) + a próxima excede (20>15) → só 1
    assert len(recent) == 1
    assert recent[0].role == "user"


@pytest.mark.asyncio
async def test_append_bumps_conversation_updated_at(db_session):
    conv = await _new_conversation(db_session)
    before = (await ConversationRepository().get_by_id(conv.uuid)).updated_at
    await MessageRepository().append(_msg(conv.uuid, "user", "nova"))
    await db_session.flush()
    after = (await ConversationRepository().get_by_id(conv.uuid)).updated_at
    assert after >= before
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/domain/conversations/test_message_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: ... message_repository`

- [ ] **Step 3: Implementar o repository**

```python
# src/domain/conversations/repositories/message_repository.py
from uuid import UUID

from sqlalchemy import func, select, update

from src.domain.conversations.entities.message import Message
from src.domain.conversations.mappers import MessageMapper
from src.domain.conversations.models.conversation import ConversationModel
from src.domain.conversations.models.message import MessageModel
from src.support.agent.ports import AgentMessage
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.settings import settings


def _estimate_tokens(text: str) -> int:
    """Heurística barata (regra 10: sem dependência nova). ~4 chars por token."""
    return max(1, len(text) // 4)


class MessageRepository:
    def __init__(self) -> None:
        self.session = CurrentAsyncSessionContext.get()

    async def append(self, message: Message) -> Message:
        model = MessageModel(**MessageMapper.to_model_attrs(message))
        self.session.add(model)
        # Bump de recência da conversa (para ordenar a sidebar por atividade).
        await self.session.execute(
            update(ConversationModel)
            .where(ConversationModel.uuid == message.conversation_id)
            .values(updated_at=func.now())
        )
        await self.session.flush()
        await self.session.refresh(model)
        return MessageMapper.to_entity(model)

    async def load_recent(self, conversation_id: UUID) -> list[AgentMessage]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.desc())
            .limit(settings.MEMORY_RECENCY_MAX_MESSAGES)
        )
        rows = (await self.session.execute(stmt)).scalars().all()  # mais novo → mais antigo

        budget = settings.MEMORY_RECENCY_TOKEN_BUDGET
        picked: list[MessageModel] = []
        used = 0
        for m in rows:
            cost = _estimate_tokens(m.content)
            if picked and used + cost > budget:
                break
            picked.append(m)
            used += cost

        picked.reverse()  # ordem cronológica para o prompt
        return [AgentMessage(role=m.role, content=m.content) for m in picked]

    async def list_by_conversation(self, conversation_id: UUID) -> list[Message]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [MessageMapper.to_entity(m) for m in rows]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/domain/conversations/test_message_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/repositories/message_repository.py tests/integration/domain/conversations/test_message_repository.py
git commit -m "feat(conversations): MessageRepository (append+bump, load_recent por budget, list)"
```

---

### Task 6: ConversationAccessPolicy (regra de ownership best-effort)

**Files:**
- Create: `src/domain/conversations/services/conversation_access_policy.py`
- Test: `tests/unit/domain/conversations/services/test_conversation_access_policy.py`

**Interfaces:**
- Consumes: `Conversation`, `UnauthorizedDomainError`.
- Produces: `ConversationAccessPolicy.assert_can_access(conversation: Conversation, user_email: str | None) -> None` — levanta `UnauthorizedDomainError` só quando ambos os e-mails são não-nulos e diferentes; caso contrário permite (best-effort, sem auth real).

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/unit/domain/conversations/services/test_conversation_access_policy.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.services.conversation_access_policy import ConversationAccessPolicy
from src.support.core.exceptions import UnauthorizedDomainError


def _conv(user_email):
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    return Conversation(uuid4(), user_email, "T", now, now, None)


def test_denies_when_both_set_and_differ():
    with pytest.raises(UnauthorizedDomainError):
        ConversationAccessPolicy.assert_can_access(_conv("a@x.com"), "b@x.com")


@pytest.mark.parametrize("owner,requester", [("a@x.com", "a@x.com"), (None, "a@x.com"), ("a@x.com", None), (None, None)])
def test_allows_when_matching_or_any_null(owner, requester):
    ConversationAccessPolicy.assert_can_access(_conv(owner), requester)  # não levanta
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/unit/domain/conversations/services/test_conversation_access_policy.py -v`
Expected: FAIL — `ModuleNotFoundError: ... conversation_access_policy`

- [ ] **Step 3: Implementar o Domain Service**

```python
# src/domain/conversations/services/conversation_access_policy.py
"""Regra de acesso a conversa — best-effort enquanto a auth não está fechada.
Domain Service (regra sem dono natural, regra 6)."""

from src.domain.conversations.entities.conversation import Conversation
from src.support.core.exceptions import UnauthorizedDomainError


class ConversationAccessPolicy:
    @staticmethod
    def assert_can_access(conversation: Conversation, user_email: str | None) -> None:
        owner = conversation.user_email
        if owner and user_email and owner != user_email:
            raise UnauthorizedDomainError("conversa pertence a outro usuário")
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/unit/domain/conversations/services/test_conversation_access_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/services/conversation_access_policy.py tests/unit/domain/conversations/services
git commit -m "feat(conversations): ConversationAccessPolicy (ownership best-effort)"
```

---

### Task 7: Reescrever AnswerQuestionAction (create/reuse conversa + grava user + recência)

**Files:**
- Modify: `src/domain/conversations/actions/answer_question_action.py` (reescrita)
- Test: `tests/unit/domain/conversations/actions/test_answer_question_action.py` (reescrita)

**Interfaces:**
- Consumes: `SearchKnowledgeBaseAction`, `OracleEnginePort`, `ConversationRepository`, `MessageRepository`, `ConversationAccessPolicy`, `NotFoundError`, `uuid7`.
- Produces: `AnswerQuestionAction(engine, search).execute(question: str, conversation_id: UUID | None, user_email: str | None) -> tuple[UUID, AsyncIterator[AgentStreamChunk]]`.
  - `conversation_id=None` → cria conversa nova (title = `question[:80]`).
  - `conversation_id` informado e inexistente → `NotFoundError`.
  - existente com dono divergente → `UnauthorizedDomainError` (via policy).
  - grava a mensagem do usuário; carrega recência **antes** de gravar (histórico = turnos anteriores); retrieval como no M1.

- [ ] **Step 1: Reescrever o teste (falho)**

Substitua **todo** o conteúdo de `tests/unit/domain/conversations/actions/test_answer_question_action.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.conversations.entities.conversation import Conversation
from src.support.agent.ports import AgentStreamChunk
from src.support.core.exceptions import NotFoundError


class _FakeSearch:
    async def execute(self, question):
        return []


class _FakeEngine:
    def __init__(self):
        self.received_history = None

    async def stream_answer(self, question, history, knowledge):
        self.received_history = history
        yield AgentStreamChunk(type="text", text="ok")


class _FakeConvRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = None

    async def get_by_id(self, cid):
        return self.existing

    async def create(self, conversation):
        self.created = conversation
        return conversation


class _FakeMsgRepo:
    def __init__(self):
        self.appended = []
        self.recent = []

    async def append(self, message):
        self.appended.append(message)
        return message

    async def load_recent(self, cid):
        return self.recent


def _make(engine, search, conv_repo, msg_repo):
    action = AnswerQuestionAction(engine=engine, search=search)
    action.conversations = conv_repo
    action.messages = msg_repo
    return action


@pytest.mark.asyncio
async def test_new_conversation_persists_user_and_sets_title():
    engine, conv_repo, msg_repo = _FakeEngine(), _FakeConvRepo(), _FakeMsgRepo()
    action = _make(engine, _FakeSearch(), conv_repo, msg_repo)

    conversation_id, stream = await action.execute("qual o onboarding?", None, "a@x.com")

    assert conv_repo.created is not None
    assert conv_repo.created.title == "qual o onboarding?"
    assert conv_repo.created.user_email == "a@x.com"
    assert conversation_id == conv_repo.created.uuid
    assert msg_repo.appended[0].role == "user"
    assert msg_repo.appended[0].content == "qual o onboarding?"
    # drena o stream
    chunks = [c async for c in stream]
    assert any(c.type == "text" for c in chunks)


@pytest.mark.asyncio
async def test_missing_conversation_id_raises_not_found():
    action = _make(_FakeEngine(), _FakeSearch(), _FakeConvRepo(existing=None), _FakeMsgRepo())
    with pytest.raises(NotFoundError):
        await action.execute("oi", uuid4(), "a@x.com")


@pytest.mark.asyncio
async def test_recency_loaded_before_appending_current_message():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    existing = Conversation(uuid4(), "a@x.com", "T", now, now, None)
    engine, msg_repo = _FakeEngine(), _FakeMsgRepo()
    from src.support.agent.ports import AgentMessage
    msg_repo.recent = [AgentMessage(role="user", content="turno anterior")]
    action = _make(engine, _FakeSearch(), _FakeConvRepo(existing=existing), msg_repo)

    _, stream = await action.execute("nova pergunta", existing.uuid, "a@x.com")
    [c async for c in stream]

    # histórico passado ao engine = turnos anteriores, sem a pergunta atual
    assert engine.received_history == [AgentMessage(role="user", content="turno anterior")]
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/unit/domain/conversations/actions/test_answer_question_action.py -v`
Expected: FAIL — a assinatura atual de `execute` não aceita `conversation_id`/`user_email`.

- [ ] **Step 3: Reescrever a Action**

Substitua **todo** o conteúdo de `src/domain/conversations/actions/answer_question_action.py`:

```python
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID

from uuid6 import uuid7

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.repositories.message_repository import MessageRepository
from src.domain.conversations.services.conversation_access_policy import ConversationAccessPolicy
from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.ports import AgentStreamChunk, OracleEnginePort
from src.support.core.exceptions import NotFoundError

_TITLE_MAX = 80


class AnswerQuestionAction:
    """Caso de uso do oráculo com memória episódica: resolve a conversa, grava a
    mensagem do usuário, carrega a recência, recupera a base (RAG clássico) e
    delega o streaming ao motor. Composição de Actions/repos + engine."""

    def __init__(self, engine: OracleEnginePort, search: SearchKnowledgeBaseAction) -> None:
        self.engine = engine
        self.search = search
        self.conversations = ConversationRepository()
        self.messages = MessageRepository()

    async def execute(
        self, question: str, conversation_id: UUID | None, user_email: str | None
    ) -> tuple[UUID, AsyncIterator[AgentStreamChunk]]:
        now = datetime.now(timezone.utc)

        if conversation_id is None:
            conversation = await self.conversations.create(
                Conversation(
                    uuid=uuid7(),
                    user_email=user_email,
                    title=question[:_TITLE_MAX],
                    created_at=now,
                    updated_at=now,
                    deleted_at=None,
                )
            )
        else:
            conversation = await self.conversations.get_by_id(conversation_id)
            if conversation is None:
                raise NotFoundError(f"conversa {conversation_id} não encontrada")
            ConversationAccessPolicy.assert_can_access(conversation, user_email)

        # Recência = turnos ANTERIORES (antes de gravar a pergunta atual, que já
        # vai ao engine como `question`).
        history = await self.messages.load_recent(conversation.uuid)

        await self.messages.append(
            Message(
                uuid=uuid7(),
                conversation_id=conversation.uuid,
                role="user",
                content=question,
                created_at=now,
            )
        )

        knowledge = await self.search.execute(question)  # sessão viva aqui
        return conversation.uuid, self.engine.stream_answer(question, history, knowledge)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/unit/domain/conversations/actions/test_answer_question_action.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/actions/answer_question_action.py tests/unit/domain/conversations/actions/test_answer_question_action.py
git commit -m "feat(conversations): AnswerQuestionAction com conversa+recência (M2)"
```

---

### Task 8: AppendAssistantMessageAction + List/Get actions

**Files:**
- Create: `src/domain/conversations/actions/append_assistant_message_action.py`
- Create: `src/domain/conversations/actions/list_conversations_action.py`
- Create: `src/domain/conversations/actions/get_conversation_action.py`
- Test: `tests/integration/domain/conversations/test_conversation_actions.py`

**Interfaces:**
- Consumes: `MessageRepository`, `ConversationRepository`, `ConversationAccessPolicy`, `Message`, `Citation`, `NotFoundError`, `uuid7`.
- Produces:
  - `AppendAssistantMessageAction().execute(conversation_id: UUID, content: str, citations: list[Citation]) -> None`
  - `ListConversationsAction().execute(user_email: str | None) -> list[Conversation]`
  - `GetConversationAction().execute(conversation_id: UUID, user_email: str | None) -> tuple[Conversation, list[Message]]` (404 se inexistente; 403 via policy)

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/integration/domain/conversations/test_conversation_actions.py
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.actions.append_assistant_message_action import (
    AppendAssistantMessageAction,
)
from src.domain.conversations.actions.get_conversation_action import GetConversationAction
from src.domain.conversations.actions.list_conversations_action import ListConversationsAction
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.shared.value_objects.citation import Citation
from src.support.core.exceptions import NotFoundError, UnauthorizedDomainError


async def _conv(db_session, user_email=None):
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    c = await ConversationRepository().create(Conversation(uuid4(), user_email, "T", now, now, None))
    await db_session.flush()
    return c


@pytest.mark.asyncio
async def test_append_assistant_persists_with_sources(db_session):
    conv = await _conv(db_session)
    cite = Citation("notion", "Doc", "https://n", "trecho", "pid")
    await AppendAssistantMessageAction().execute(conv.uuid, "resposta final", [cite])
    await db_session.flush()

    _, messages = await GetConversationAction().execute(conv.uuid, None)
    assert len(messages) == 1
    assert messages[0].role == "assistant"
    assert messages[0].content == "resposta final"
    assert messages[0].sources == [cite]


@pytest.mark.asyncio
async def test_get_conversation_not_found_raises(db_session):
    with pytest.raises(NotFoundError):
        await GetConversationAction().execute(uuid4(), None)


@pytest.mark.asyncio
async def test_get_conversation_denies_other_owner(db_session):
    conv = await _conv(db_session, user_email="a@x.com")
    with pytest.raises(UnauthorizedDomainError):
        await GetConversationAction().execute(conv.uuid, "b@x.com")


@pytest.mark.asyncio
async def test_list_conversations_by_user(db_session):
    await _conv(db_session, user_email="a@x.com")
    result = await ListConversationsAction().execute("a@x.com")
    assert all(c.user_email == "a@x.com" for c in result)
    assert len(result) >= 1
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/domain/conversations/test_conversation_actions.py -v`
Expected: FAIL — `ModuleNotFoundError` nas actions novas.

- [ ] **Step 3: Implementar as três Actions**

```python
# src/domain/conversations/actions/append_assistant_message_action.py
from datetime import datetime, timezone
from uuid import UUID

from uuid6 import uuid7

from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.message_repository import MessageRepository
from src.domain.shared.value_objects.citation import Citation


class AppendAssistantMessageAction:
    """Persiste a resposta do oráculo após o streaming terminar. Chamada dentro
    de run_in_async_session (sessão própria, fora do request)."""

    def __init__(self) -> None:
        self.messages = MessageRepository()

    async def execute(
        self, conversation_id: UUID, content: str, citations: list[Citation]
    ) -> None:
        await self.messages.append(
            Message(
                uuid=uuid7(),
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                created_at=datetime.now(timezone.utc),
                sources=list(citations) if citations else None,
            )
        )
```

```python
# src/domain/conversations/actions/list_conversations_action.py
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository


class ListConversationsAction:
    def __init__(self) -> None:
        self.conversations = ConversationRepository()

    async def execute(self, user_email: str | None) -> list[Conversation]:
        return await self.conversations.list_by_user(user_email)
```

```python
# src/domain/conversations/actions/get_conversation_action.py
from uuid import UUID

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.repositories.message_repository import MessageRepository
from src.domain.conversations.services.conversation_access_policy import ConversationAccessPolicy
from src.support.core.exceptions import NotFoundError


class GetConversationAction:
    def __init__(self) -> None:
        self.conversations = ConversationRepository()
        self.messages = MessageRepository()

    async def execute(
        self, conversation_id: UUID, user_email: str | None
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self.conversations.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(f"conversa {conversation_id} não encontrada")
        ConversationAccessPolicy.assert_can_access(conversation, user_email)
        messages = await self.messages.list_by_conversation(conversation_id)
        return conversation, messages
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/domain/conversations/test_conversation_actions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/conversations/actions/append_assistant_message_action.py src/domain/conversations/actions/list_conversations_action.py src/domain/conversations/actions/get_conversation_action.py tests/integration/domain/conversations/test_conversation_actions.py
git commit -m "feat(conversations): actions de persistir resposta, listar e abrir conversa"
```

---

### Task 9: Novo contrato do `/ask` — request, controller, evento `conversation`, persistência pós-stream

**Files:**
- Modify: `src/app/api/requests/ask_question_request.py` (remove `history`, adiciona `conversation_id`)
- Modify: `src/app/api/controllers/conversation_controller.py` (novo fluxo do `ask`)
- Test: `tests/integration/api/test_ask_endpoint.py` (reescrita ao novo contrato)

**Interfaces:**
- Consumes: `AnswerQuestionAction` (Task 7), `AppendAssistantMessageAction` (Task 8), `run_in_async_session` (Task 1), `get_oracle_engine`, `get_embeddings_client`, `SearchKnowledgeBaseAction`.
- Produces:
  - `AskQuestionRequest { question: str, conversation_id: UUID | None = None }`.
  - `ConversationController.ask` emite SSE na ordem: `conversation` → `token`* → `sources` → (persiste assistant, se houve texto e não falhou) → `done`. Em falha, emite `error` e não persiste.

- [ ] **Step 1: Reescrever o teste (falho)**

Substitua **todo** o conteúdo de `tests/integration/api/test_ask_endpoint.py`:

```python
from typing import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True)
async def _dispose_db_engine_between_tests():
    yield
    from src.support.core.database import engine

    await engine.dispose()


class FailingOracleEngine:
    async def stream_answer(self, question, history, knowledge=None) -> AsyncIterator:
        from src.support.agent.ports import AgentStreamChunk

        yield AgentStreamChunk(type="text", text="ola ")
        raise RuntimeError("boom: engine caiu no meio do stream")


def _parse_conversation_id(body: str) -> str:
    # localiza o bloco "event: conversation" e lê o data da linha seguinte
    import json

    blocks = body.split("\n\n")
    for b in blocks:
        if "event: conversation" in b:
            data_line = next(l for l in b.split("\n") if l.startswith("data:"))
            return json.loads(data_line[5:].strip())["id"]
    raise AssertionError("evento 'conversation' não emitido")


@pytest.mark.asyncio
async def test_ask_streams_and_persists_both_turns(monkeypatch):
    import src.app.api.controllers.conversation_controller as ctrl
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient
    from tests.fakes.fake_oracle_engine import FakeOracleEngine

    monkeypatch.setattr(ctrl, "get_oracle_engine", lambda: FakeOracleEngine(answer="resposta de teste"))
    monkeypatch.setattr(ctrl, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversations/ask",
            json={"question": "o que é o onboarding?"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "event: conversation" in body
        assert "resposta" in body
        assert "event: sources" in body
        assert "event: done" in body

    conversation_id = UUID(_parse_conversation_id(body))

    # verifica persistência num escopo de sessão próprio
    from src.support.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                text("SELECT role FROM messages WHERE conversation_id = :cid ORDER BY created_at"),
                {"cid": conversation_id},
            )
        ).scalars().all()
        assert rows == ["user", "assistant"]
        # cleanup (evita acúmulo entre execuções)
        await s.execute(text("DELETE FROM conversations WHERE uuid = :cid"), {"cid": conversation_id})
        await s.commit()


@pytest.mark.asyncio
async def test_ask_failure_emits_error_and_does_not_persist_assistant(monkeypatch):
    import src.app.api.controllers.conversation_controller as ctrl
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient

    monkeypatch.setattr(ctrl, "get_oracle_engine", lambda: FailingOracleEngine())
    monkeypatch.setattr(ctrl, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/conversations/ask", json={"question": "o que é o onboarding?"})
        assert resp.status_code == 200
        body = resp.text
        assert "event: error" in body
        assert "event: done" in body

    conversation_id = UUID(_parse_conversation_id(body))
    from src.support.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        roles = (
            await s.execute(
                text("SELECT role FROM messages WHERE conversation_id = :cid"),
                {"cid": conversation_id},
            )
        ).scalars().all()
        assert "assistant" not in roles  # resposta parcial NÃO foi persistida
        await s.execute(text("DELETE FROM conversations WHERE uuid = :cid"), {"cid": conversation_id})
        await s.commit()
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/api/test_ask_endpoint.py -v`
Expected: FAIL — o `ask` atual não emite `event: conversation` nem persiste; request ainda exige `history`.

- [ ] **Step 3: Atualizar o request schema**

Substitua **todo** o conteúdo de `src/app/api/requests/ask_question_request.py`:

```python
from uuid import UUID

from pydantic import BaseModel, Field


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: UUID | None = None
```

- [ ] **Step 4: Reescrever o controller `ask`**

Substitua **todo** o conteúdo de `src/app/api/controllers/conversation_controller.py`:

```python
import json
import logging
from typing import AsyncIterator
from uuid import UUID

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.app.api.requests.ask_question_request import AskQuestionRequest
from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.conversations.actions.append_assistant_message_action import (
    AppendAssistantMessageAction,
)
from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.oracle_engine import get_oracle_engine
from src.support.clients.embeddings.embeddings_client import get_embeddings_client
from src.support.core.session_scope import run_in_async_session

logger = logging.getLogger(__name__)

_USER_EMAIL_HEADER = "cf-access-authenticated-user-email"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _citation_payload(c) -> dict:
    return {"source_type": c.source_type, "title": c.title, "url": c.url, "snippet": c.snippet}


class ConversationController:
    @staticmethod
    async def ask(request: Request, data: AskQuestionRequest) -> StreamingResponse:
        user_email = request.headers.get(_USER_EMAIL_HEADER)
        search = SearchKnowledgeBaseAction(embeddings=get_embeddings_client())
        action = AnswerQuestionAction(engine=get_oracle_engine(), search=search)

        # Conversa + user message são gravadas aqui (sessão do request viva).
        conversation_id, stream = await action.execute(
            data.question, data.conversation_id, user_email
        )

        captured: dict = {"text": "", "citations": []}

        async def event_source() -> AsyncIterator[str]:
            yield _sse("conversation", {"id": str(conversation_id)})
            failed = False
            try:
                async for chunk in stream:
                    if chunk.type == "text":
                        captured["text"] += chunk.text
                        yield _sse("token", {"text": chunk.text})
                    elif chunk.type == "sources":
                        captured["citations"] = chunk.citations
                        yield _sse(
                            "sources",
                            {"citations": [_citation_payload(c) for c in chunk.citations]},
                        )
            except Exception:
                failed = True
                logger.exception("stream falhou durante /conversations/ask")
                yield _sse("error", {"message": "erro ao gerar a resposta"})

            # Persiste a resposta só quando o stream terminou com sucesso e há texto.
            if not failed and captured["text"]:
                try:
                    await _persist_assistant(
                        conversation_id, captured["text"], captured["citations"]
                    )
                except Exception:
                    logger.exception("falha ao persistir a resposta do oráculo")

            yield _sse("done", {})

        return StreamingResponse(event_source(), media_type="text/event-stream")


async def _persist_assistant(conversation_id: UUID, content: str, citations: list) -> None:
    async def _work() -> None:
        await AppendAssistantMessageAction().execute(conversation_id, content, citations)

    await run_in_async_session(_work)
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/api/test_ask_endpoint.py -v`
Expected: PASS (ambos os testes)

- [ ] **Step 6: Commit**

```bash
git add src/app/api/requests/ask_question_request.py src/app/api/controllers/conversation_controller.py tests/integration/api/test_ask_endpoint.py
git commit -m "feat(api): /ask com conversation_id + persistência pós-stream (M2)"
```

---

### Task 10: Endpoints de listar e abrir conversa

**Files:**
- Create: `src/app/api/responses/conversation_responses.py`
- Modify: `src/app/api/controllers/conversation_controller.py` (adicionar `list` e `get`)
- Modify: `src/app/api/routes/conversations.py` (registrar as rotas GET)
- Test: `tests/integration/api/test_conversation_endpoints.py`

**Interfaces:**
- Consumes: `ListConversationsAction`, `GetConversationAction` (Task 8).
- Produces:
  - `GET /conversations` → `list[ConversationSummaryResponse]` (`{id, title, updated_at}`).
  - `GET /conversations/{conversation_id}` → `ConversationDetailResponse` (`{id, title, messages: [{role, content, sources}]}`).

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/integration/api/test_conversation_endpoints.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    from src.support.core.database import engine

    await engine.dispose()


async def _seed_conversation(user_email: str):
    from datetime import datetime, timezone
    from uuid import uuid4

    from src.domain.conversations.entities.conversation import Conversation
    from src.domain.conversations.entities.message import Message
    from src.domain.conversations.repositories.conversation_repository import ConversationRepository
    from src.domain.conversations.repositories.message_repository import MessageRepository
    from src.domain.shared.value_objects.citation import Citation
    from src.support.core.session_scope import run_in_async_session

    cid = uuid4()
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)

    async def _work():
        await ConversationRepository().create(
            Conversation(cid, user_email, "Título da conversa", now, now, None)
        )
        from uuid6 import uuid7

        await MessageRepository().append(
            Message(uuid7(), cid, "user", "pergunta", now)
        )
        await MessageRepository().append(
            Message(
                uuid7(), cid, "assistant", "resposta", now,
                sources=[Citation("notion", "Doc", "https://n", "s", "pid")],
            )
        )

    await run_in_async_session(_work)
    return cid


@pytest.mark.asyncio
async def test_list_and_get_conversation():
    email = "lister@x.com"
    cid = await _seed_conversation(email)
    from main import app

    transport = ASGITransport(app=app)
    headers = {"Cf-Access-Authenticated-User-Email": email}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        listing = await client.get("/conversations", headers=headers)
        assert listing.status_code == 200
        ids = [c["id"] for c in listing.json()]
        assert str(cid) in ids

        detail = await client.get(f"/conversations/{cid}", headers=headers)
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["title"] == "Título da conversa"
        assert [m["role"] for m in payload["messages"]] == ["user", "assistant"]
        assert payload["messages"][1]["sources"][0]["title"] == "Doc"

    # cleanup
    from src.support.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        await s.execute(text("DELETE FROM conversations WHERE uuid = :cid"), {"cid": cid})
        await s.commit()


@pytest.mark.asyncio
async def test_get_missing_conversation_returns_404():
    from uuid import uuid4

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/conversations/{uuid4()}")
        assert resp.status_code == 404
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/api/test_conversation_endpoints.py -v`
Expected: FAIL — rotas `GET /conversations` e `/{id}` ainda não existem (404 na listagem / método não encontrado).

- [ ] **Step 3: Criar os response schemas**

```python
# src/app/api/responses/conversation_responses.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CitationResponse(BaseModel):
    source_type: str
    title: str
    url: str
    snippet: str
    page_id: str | None = None


class MessageResponse(BaseModel):
    role: str
    content: str
    sources: list[CitationResponse] | None = None

    @classmethod
    def from_entity(cls, m) -> "MessageResponse":
        sources = (
            [
                CitationResponse(
                    source_type=c.source_type,
                    title=c.title,
                    url=c.url,
                    snippet=c.snippet,
                    page_id=c.page_id,
                )
                for c in m.sources
            ]
            if m.sources
            else None
        )
        return cls(role=m.role, content=m.content, sources=sources)


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str | None
    updated_at: datetime

    @classmethod
    def from_entity(cls, c) -> "ConversationSummaryResponse":
        return cls(id=c.uuid, title=c.title, updated_at=c.updated_at)


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str | None
    messages: list[MessageResponse]

    @classmethod
    def from_entity(cls, c, messages) -> "ConversationDetailResponse":
        return cls(
            id=c.uuid,
            title=c.title,
            messages=[MessageResponse.from_entity(m) for m in messages],
        )
```

- [ ] **Step 4: Adicionar `list` e `get` ao controller**

Em `src/app/api/controllers/conversation_controller.py`, adicione os imports no topo (junto aos demais):

```python
from src.app.api.responses.conversation_responses import (
    ConversationDetailResponse,
    ConversationSummaryResponse,
)
from src.domain.conversations.actions.get_conversation_action import GetConversationAction
from src.domain.conversations.actions.list_conversations_action import ListConversationsAction
```

E dentro da classe `ConversationController`, após o método `ask`, adicione:

```python
    @staticmethod
    async def list(request: Request) -> list[ConversationSummaryResponse]:
        user_email = request.headers.get(_USER_EMAIL_HEADER)
        conversations = await ListConversationsAction().execute(user_email)
        return [ConversationSummaryResponse.from_entity(c) for c in conversations]

    @staticmethod
    async def get(request: Request, conversation_id: UUID) -> ConversationDetailResponse:
        user_email = request.headers.get(_USER_EMAIL_HEADER)
        conversation, messages = await GetConversationAction().execute(
            conversation_id, user_email
        )
        return ConversationDetailResponse.from_entity(conversation, messages)
```

- [ ] **Step 5: Registrar as rotas**

Substitua **todo** o conteúdo de `src/app/api/routes/conversations.py`:

```python
"""Rota do oráculo — pública no nível da app (protegida por Cloudflare Access na borda)."""

from fastapi import APIRouter

from src.app.api.controllers.conversation_controller import ConversationController

public_router = APIRouter(prefix="/conversations", tags=["Conversations"])
public_router.post("/ask")(ConversationController.ask)
public_router.get("")(ConversationController.list)
public_router.get("/{conversation_id}")(ConversationController.get)
```

- [ ] **Step 6: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/api/test_conversation_endpoints.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/app/api/responses/conversation_responses.py src/app/api/controllers/conversation_controller.py src/app/api/routes/conversations.py tests/integration/api/test_conversation_endpoints.py
git commit -m "feat(api): GET /conversations e /conversations/{id} (M2)"
```

---

### Task 11: UI mínima — sidebar de conversas e continuidade

**Files:**
- Modify: `src/app/web/index.html` (sidebar + `conversation_id` + reabrir)
- Test: `tests/integration/api/test_web_ui.py` (adicionar asserção dos novos elementos)

**Interfaces:**
- Consumes: `GET /conversations`, `GET /conversations/{id}`, `POST /conversations/ask` (evento SSE `conversation`).
- Produces: página com lista de conversas, botão "Nova conversa", render de turnos ao reabrir, e `conversation_id` mantido em `localStorage`.

- [ ] **Step 1: Adicionar asserção no teste da página**

Em `tests/integration/api/test_web_ui.py`, ao final da função `test_root_serves_chat_page`, adicione (mantendo as asserções atuais):

```python
        assert 'id="conversations"' in resp.text  # sidebar de conversas
        assert "Nova conversa" in resp.text
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/integration/api/test_web_ui.py -v`
Expected: FAIL — os novos marcadores ainda não existem no HTML.

- [ ] **Step 3: Reescrever a UI**

Substitua **todo** o conteúdo de `src/app/web/index.html`:

```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Oracle Borderless</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; display: flex; min-height: 100vh; }
    #sidebar { width: 260px; border-right: 1px solid #ddd; padding: 1rem; box-sizing: border-box; }
    #sidebar h2 { font-size: 1rem; }
    #conversations { list-style: none; padding: 0; margin: .5rem 0; }
    #conversations li { padding: .4rem .5rem; border-radius: 6px; cursor: pointer; font-size: .9rem; }
    #conversations li:hover { background: #f2f2f2; }
    #main { flex: 1; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    #answer { white-space: pre-wrap; border: 1px solid #ddd; border-radius: 8px; padding: 1rem; min-height: 4rem; }
    #history { margin-bottom: 1rem; }
    .turn { border: 1px solid #eee; border-radius: 8px; padding: .5rem .75rem; margin-bottom: .5rem; }
    .turn .role { font-weight: bold; font-size: .8rem; color: #666; }
    #sources { margin-top: 1rem; font-size: .9rem; color: #555; }
    input, button { font-size: 1rem; padding: .5rem; }
    #q { width: 100%; box-sizing: border-box; margin-bottom: .5rem; }
  </style>
</head>
<body>
  <aside id="sidebar">
    <h2>Conversas</h2>
    <button id="new">Nova conversa</button>
    <ul id="conversations"></ul>
  </aside>
  <main id="main">
    <h1>Oracle Borderless</h1>
    <div id="history"></div>
    <input id="q" placeholder="Faça sua pergunta..." />
    <button id="send">Perguntar</button>
    <h3>Resposta</h3>
    <div id="answer"></div>
    <div id="sources"></div>
  </main>
  <script>
    const answerEl = document.getElementById("answer");
    const sourcesEl = document.getElementById("sources");
    const historyEl = document.getElementById("history");
    const listEl = document.getElementById("conversations");
    let conversationId = localStorage.getItem("conversationId") || null;

    function setConversation(id) {
      conversationId = id;
      if (id) localStorage.setItem("conversationId", id);
      else localStorage.removeItem("conversationId");
    }

    function renderSources(container, citations) {
      container.innerHTML = "";
      if (!citations || !citations.length) return;
      const strong = document.createElement("strong");
      strong.textContent = "Fontes:";
      container.appendChild(strong);
      container.appendChild(document.createElement("br"));
      citations.forEach((c, i) => {
        if (i > 0) container.appendChild(document.createElement("br"));
        container.appendChild(document.createTextNode("• "));
        let safeUrl = null;
        try {
          const parsed = new URL(c.url);
          if (parsed.protocol === "http:" || parsed.protocol === "https:") safeUrl = parsed.href;
        } catch (e) { safeUrl = null; }
        if (safeUrl) {
          const link = document.createElement("a");
          link.setAttribute("href", safeUrl);
          link.textContent = c.title;
          container.appendChild(link);
        } else {
          container.appendChild(document.createTextNode(c.title));
        }
        container.appendChild(document.createTextNode(" (" + c.source_type + ")"));
      });
    }

    async function loadConversations() {
      const resp = await fetch("/conversations");
      if (!resp.ok) return;
      const items = await resp.json();
      listEl.innerHTML = "";
      items.forEach(c => {
        const li = document.createElement("li");
        li.textContent = c.title || "(sem título)";
        li.onclick = () => openConversation(c.id);
        listEl.appendChild(li);
      });
    }

    async function openConversation(id) {
      const resp = await fetch("/conversations/" + id);
      if (!resp.ok) return;
      const data = await resp.json();
      setConversation(id);
      answerEl.textContent = "";
      sourcesEl.innerHTML = "";
      historyEl.innerHTML = "";
      data.messages.forEach(m => {
        const turn = document.createElement("div");
        turn.className = "turn";
        const role = document.createElement("div");
        role.className = "role";
        role.textContent = m.role === "user" ? "Você" : "Oráculo";
        turn.appendChild(role);
        turn.appendChild(document.createTextNode(m.content));
        if (m.sources) {
          const s = document.createElement("div");
          renderSources(s, m.sources);
          turn.appendChild(s);
        }
        historyEl.appendChild(turn);
      });
    }

    document.getElementById("new").onclick = () => {
      setConversation(null);
      historyEl.innerHTML = "";
      answerEl.textContent = "";
      sourcesEl.innerHTML = "";
    };

    document.getElementById("send").onclick = async () => {
      answerEl.textContent = "";
      sourcesEl.innerHTML = "";
      const question = document.getElementById("q").value;
      const resp = await fetch("/conversations/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, conversation_id: conversationId }),
      });
      if (!resp.ok) { answerEl.textContent = "Erro: " + resp.status; return; }
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
          if (type === "conversation") setConversation(data.id);
          if (type === "token") answerEl.textContent += data.text;
          if (type === "error") answerEl.textContent += "\n[erro: " + data.message + "]";
          if (type === "sources") renderSources(sourcesEl, data.citations);
        }
      }
      loadConversations();  // atualiza a sidebar após o turno
    };

    loadConversations();
    if (conversationId) openConversation(conversationId);
  </script>
</body>
</html>
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/integration/api/test_web_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app/web/index.html tests/integration/api/test_web_ui.py
git commit -m "feat(web): sidebar de conversas + continuidade por conversation_id (M2)"
```

---

### Task 12: Suíte completa + verificação de fronteira

**Files:** nenhum novo — validação de regressão de todo o M1 + M2.

- [ ] **Step 1: Rodar toda a suíte**

Run: `python -m pytest -q` (com `DB_PORT` apontando para o pgvector, se necessário)
Expected: todos verdes (unit + integração de M1 e M2).

- [ ] **Step 2: Confirmar que o domínio não importa infra proibida**

Run:
```bash
grep -rEn "import (fastapi|pydantic)|from (fastapi|pydantic)" src/domain/conversations/entities src/domain/conversations/actions src/domain/conversations/repositories src/domain/conversations/services || echo "OK: domínio limpo"
```
Expected: `OK: domínio limpo` (entities/actions/repos/services não importam FastAPI nem Pydantic).

- [ ] **Step 3: Confirmar o app e o metadata do Alembic**

Run:
```bash
python -c "from main import app; print('APP OK')"
alembic check
```
Expected: `APP OK` e "No new upgrade operations detected."

- [ ] **Step 4: Commit final (se houver ajuste)**

```bash
git add -A
git commit -m "test(conversations): fecha M2 — suíte completa verde" --allow-empty
```

---

## Self-Review

**1. Cobertura do spec (§ por §):**
- §2 data model → Task 2 (entities, models, migration). ✅
- §3 recência por token budget → Task 1 (settings) + Task 5 (`load_recent`). ✅
- §4 repositories & actions → Tasks 4, 5, 7, 8. ✅
- §5 persistência pós-stream + ownership → Task 1 (helper), Task 9 (fluxo no controller), Task 6 (policy). ✅
- §6 API & UI → Tasks 9, 10 (endpoints/responses), Task 11 (UI). ✅
- §7 testes → tests embutidos em cada task; Task 12 fecha a regressão. ✅
- §8 breaking change do request → Task 9 (reescrita do request + teste). ✅

**2. Placeholders:** nenhum "TBD"/"TODO"/"adicione tratamento apropriado". Todo passo tem código real. ✅

**3. Consistência de tipos/nomes:** `AnswerQuestionAction.execute(question, conversation_id, user_email) -> tuple[UUID, AsyncIterator]` (Task 7) é consumido igual no controller (Task 9). `MessageRepository.append/load_recent/list_by_conversation`, `ConversationRepository.get_by_id/create/list_by_user` consistentes entre Tasks 4/5 e consumidores 7/8/10. `run_in_async_session(fn)` (Task 1) usado em Task 9/10. `_USER_EMAIL_HEADER` definido no controller (Task 9) e reusado em Task 10. Response `from_entity` consistente com as entities. ✅

**Nota de risco resolvida:** o spec §5 previa `response.background` como caminho primário. Ao inspecionar `BackgroundTaskMiddleware`, confirmei que ele fotografa as tasks **antes** do corpo SSE ser gerado — então tasks adicionadas durante o streaming não seriam executadas. O plano adota o caminho robusto (o "fallback" do spec): persistir no fim do próprio gerador via `run_in_async_session` (sessão própria, padrão Job/Seed). Mesmo requisito atendido (assistant persistido após o stream, sessão própria, nada em falha), de forma determinística.

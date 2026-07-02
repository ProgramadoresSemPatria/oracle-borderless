# Guia de Testes

Este guia define estrutura e práticas de teste para a arquitetura-alvo. Adapta a pirâmide clássica (70/20/10 entre unit/integration/e2e) ao contexto específico — aplicação com **separação Entity/Model**, **context vars por request** e **dual engine SQLAlchemy**.

Para arquitetura geral, ver `docs/architecture.md`. Dependências dev (`pytest`, `pytest-asyncio`, `httpx`, `faker`, `factory-boy`) ficam em `pyproject.toml`.

## Filosofia

1. **Teste comportamento, não implementação.** Testes que sobrevivem a refatorações.
2. **Pirâmide:** muitos unit rápidos, menos integration, poucos e2e.
3. **Domínio é o mais testado.** Entities, Actions, Domain Services concentram a regra — concentram o teste.
4. **Entity é trivial de testar.** Aproveite — teste comportamento de entidade extensivamente.
5. **Context vars exigem cuidado.** Muitos bugs emergem quando o contexto não está populado.

## Estrutura

```
tests/
├── conftest.py                          # fixtures globais
├── fakes/
│   └── (in-memory implementations)
├── unit/                                # rápidos, sem I/O
│   └── domain/
│       └── documents/
│           ├── entities/
│           │   └── test_document.py     # comportamento da Entity
│           ├── actions/
│           │   ├── test_ingest_document_action.py
│           │   └── test_list_documents_action.py
│           └── services/                # Domain Services (raros)
├── integration/                         # com banco real
│   ├── conftest.py
│   └── domain/
│       └── documents/
│           └── repositories/
│               └── test_document_repository.py
└── e2e/                                 # via TestClient
    ├── conftest.py
    └── api/
        └── test_document_endpoints.py
```

A estrutura de `tests/` espelha `src/` — fica óbvio onde o teste vive.

## Fixtures críticas deste projeto

O projeto usa **ContextVars** para request e sessão:

- `CurrentRequestContext` (Request atual; usuário quando a auth existir)
- `CurrentAsyncSessionContext`
- `CurrentSessionContext`
- `BackgroundTaskContext`

**Testes precisam populá-las** quando testam código que as consome. Sem isso, pega `RuntimeError: No active database session found in context`.

### `conftest.py` global

```python
# tests/conftest.py
import pytest
from fastapi import BackgroundTasks

from src.support.core.context import (
    CurrentRequestContext,
    CurrentAsyncSessionContext,
    CurrentSessionContext,
    BackgroundTaskContext,
)


@pytest.fixture(autouse=True)
def reset_contexts():
    """Limpa todos os contextos antes e depois de cada teste."""
    CurrentRequestContext.reset()
    CurrentAsyncSessionContext.reset()
    CurrentSessionContext.reset()
    yield
    CurrentRequestContext.reset()
    CurrentAsyncSessionContext.reset()
    CurrentSessionContext.reset()


@pytest.fixture
def background_tasks_context():
    bg = BackgroundTasks()
    BackgroundTaskContext.set(bg)
    return bg
```

**Por que `autouse=True`:** garante limpeza entre testes, evitando vazamento de sessão. Crítico em suite paralela.

### Fixture de banco para integração

```python
# tests/integration/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.support.core.settings import settings
from src.support.core.models.base_model import BaseModel
from src.support.core.context import CurrentAsyncSessionContext


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Engine dedicado para testes."""
    test_url = settings.DATABASE_URL_TEST
    engine = create_async_engine(test_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Session com rollback automático no teardown."""
    async with test_engine.connect() as connection:
        trans = await connection.begin()

        SessionTest = sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        session = SessionTest()
        CurrentAsyncSessionContext.set(session)

        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            CurrentAsyncSessionContext.reset()
```

**Padrão:** cada teste roda em transação própria com rollback no teardown — isolamento perfeito.

> **Autenticação:** ainda é ponto em aberto. Quando existir, adicione aqui uma fixture que popula o usuário no `CurrentRequestContext` (`CurrentRequestContext.set_user(...)`) para os testes que dependem de um usuário autenticado.

## Testando Entities

Entities são **dataclasses puras** — mais fácil tipo de teste. Aproveite para cobrir extensivamente o comportamento de domínio.

```python
# tests/unit/domain/documents/entities/test_document.py
from datetime import datetime
from uuid import uuid4

from src.domain.documents.entities.document import Document


def make_document(**overrides) -> Document:
    """Helper local para construir Document com defaults sensatos."""
    defaults = dict(
        uuid=uuid4(),
        notion_page_id="page-123",
        title="Regras de matrícula",
        content="...",
        source_url="https://notion.so/page-123",
        status="approved",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return Document(**{**defaults, **overrides})


def test_approved_document_is_approved():
    document = make_document(status="approved")
    assert document.is_approved() is True


def test_pending_document_is_not_approved():
    document = make_document(status="pending")
    assert document.is_approved() is False


def test_soft_deleted_document_is_not_approved():
    document = make_document(deleted_at=datetime.utcnow())
    assert document.is_approved() is False


def test_approved_document_is_indexable():
    document = make_document(status="approved")
    assert document.is_indexable() is True
```

**Nenhum mock, nenhuma fixture, nenhum I/O.** Esse é o paraíso da pirâmide de testes — invista pesado aqui.

## Testando Actions

Actions têm dependências (Repositories, Clients). Use fakes ou mocks.

### Action sem clients externos

```python
# tests/unit/domain/documents/actions/test_list_documents_action.py
import pytest

from src.domain.documents.actions.list_documents_action import ListDocumentsAction


@pytest.mark.asyncio
async def test_lists_non_deleted_documents(db_session):
    from database.factories.document_factory import DocumentFactory
    from datetime import datetime

    DocumentFactory._meta.sqlalchemy_session = db_session
    await DocumentFactory.create_batch(5)
    await DocumentFactory.create(deleted_at=datetime.utcnow())  # soft-deleted

    action = ListDocumentsAction()
    documents = await action.execute(skip=0, limit=100)

    assert len(documents) == 5  # só não-deletados
```

### Action com client externo (Notion via MCP)

```python
# tests/unit/domain/documents/actions/test_ingest_document_action.py
from unittest.mock import AsyncMock
import pytest

from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.dtos.document_data import DocumentIngestData
from src.support.core.exceptions import DomainConflictError


@pytest.mark.asyncio
async def test_ingests_approved_document(db_session):
    mock_notion = AsyncMock()
    mock_notion.get_page.return_value = _fake_page(is_approved=True)

    action = IngestDocumentAction(notion_client=mock_notion)

    document = await action.execute(DocumentIngestData(notion_page_id="page-123"))

    assert document.notion_page_id == "page-123"
    assert document.is_approved()
    mock_notion.get_page.assert_awaited_once()


@pytest.mark.asyncio
async def test_raises_conflict_when_document_already_ingested(db_session):
    from database.factories.document_factory import DocumentFactory
    DocumentFactory._meta.sqlalchemy_session = db_session

    await DocumentFactory.create(notion_page_id="page-123")

    mock_notion = AsyncMock()
    mock_notion.get_page.return_value = _fake_page(is_approved=True)

    action = IngestDocumentAction(notion_client=mock_notion)

    with pytest.raises(DomainConflictError) as exc_info:
        await action.execute(DocumentIngestData(notion_page_id="page-123"))

    assert "já foi ingerido" in str(exc_info.value)
```

**Padrão:** clients externos (Notion/MCP, LLM) são mockados — testes não devem fazer I/O externo. Repository usa banco real via `db_session` fixture.

## Testando Repositories

Foco: garantir que **conversão Entity ↔ Model funciona** e que filtros aplicam corretamente.

```python
# tests/integration/domain/documents/repositories/test_document_repository.py
import pytest
from datetime import datetime

from src.domain.documents.repositories.document_repository import DocumentRepository


@pytest.mark.asyncio
async def test_get_by_id_returns_document_entity(db_session):
    from database.factories.document_factory import DocumentFactory
    DocumentFactory._meta.sqlalchemy_session = db_session

    document_model = await DocumentFactory.create(title="Regras")

    repository = DocumentRepository()
    document_entity = await repository.get_by_id(document_model.uuid)

    assert document_entity is not None
    assert document_entity.title == "Regras"
    # Crucial: verifica que retornou Entity, não Model
    from src.domain.documents.entities.document import Document
    assert isinstance(document_entity, Document)


@pytest.mark.asyncio
async def test_get_by_id_excludes_deleted_by_default(db_session):
    from database.factories.document_factory import DocumentFactory
    DocumentFactory._meta.sqlalchemy_session = db_session

    document_model = await DocumentFactory.create(deleted_at=datetime.utcnow())

    repository = DocumentRepository()

    assert await repository.get_by_id(document_model.uuid) is None
    assert await repository.get_by_id(document_model.uuid, with_trashed=True) is not None
```

## Testando Domain Services

Domain Services são puros (sem I/O) — testes são triviais.

```python
# tests/unit/domain/documents/services/test_content_sanitizer_service.py
from src.domain.documents.services.content_sanitizer_service import ContentSanitizerService


def test_flags_confidential_content():
    service = ContentSanitizerService()
    result = service.check("Este documento é CONFIDENCIAL e restrito.")
    assert result.is_safe is False
    assert "confidencial" in result.flagged_terms


def test_allows_clean_content():
    service = ContentSanitizerService()
    result = service.check("Regras públicas de matrícula.")
    assert result.is_safe is True
    assert result.flagged_terms == []
```

## Testando Jobs

Jobs têm dois aspectos:
1. **Lógica em `action()`** (o caso de uso).
2. **Mecanismo de lock/tracking** (geralmente confiamos na classe base `Job`).

```python
# tests/unit/app/console/jobs/test_sync_knowledge_base_job.py
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_sync_ingests_new_approved_pages(db_session, monkeypatch):
    from src.app.console.jobs.sync_knowledge_base_job import SyncKnowledgeBaseJob

    # o Job delega para a Action; mockamos o Notion na fronteira
    job = SyncKnowledgeBaseJob()
    await job.action()  # chama direto, sem lock/tracking

    from src.domain.documents.repositories.document_repository import DocumentRepository
    documents = await DocumentRepository().list_documents()

    assert len(documents) >= 0
```

**Dica:** teste `action()` diretamente. O `execute()` (com lock + tracking) é responsabilidade da base `Job` — testar uma vez é suficiente.

## Testando endpoints (e2e)

```python
# tests/e2e/conftest.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)
```

```python
# tests/e2e/api/test_document_endpoints.py
def test_list_documents_endpoint(client):
    response = client.get("/documents")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_ingest_document_via_api(client, mock_notion):
    mock_notion.get_page.return_value = _fake_page(is_approved=True)

    response = client.post("/documents", json={"notion_page_id": "page-123"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "approved"
```

**Complicação em e2e:** `TestClient` sobe a app inteira, **incluindo middlewares**. Clients externos (Notion/MCP, LLM) devem ser mockados via `monkeypatch` ou override de dependency — nunca chamados de verdade num teste.

> Quando a autenticação existir, os testes e2e precisarão de um cliente autenticado (token válido ou override da dependency de auth). Documentar aqui quando definido.

## Fakes vs mocks

### Fakes (preferíveis)

```python
# tests/fakes/in_memory_document_repository.py
from uuid import UUID
from src.domain.documents.entities.document import Document


class InMemoryDocumentRepository:
    """Implementação in-memory para testes unitários sem banco."""

    def __init__(self):
        self._documents: dict[UUID, Document] = {}

    async def create(self, document: Document) -> Document:
        self._documents[document.uuid] = document
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self._documents.get(document_id)

    async def get_by_notion_page_id(self, page_id: str) -> Document | None:
        return next((d for d in self._documents.values() if d.notion_page_id == page_id), None)
```

Use quando a Action sob teste pode receber Repository como dependência opcional (no teste, injete o fake; em produção, usa o real).

### Mocks (use para Clients externos)

```python
mock_notion = AsyncMock()
mock_notion.get_page.return_value = _fake_page(is_approved=True)
```

Use quando: integração externa que você não quer chamar de verdade (Notion/MCP, LLM).

**Regra prática:** **Fakes para domínio, Mocks para infraestrutura.**

## Convenções de nome

- Arquivos: `test_{modulo}.py`.
- Funções: `test_{comportamento_esperado}`.
- **Nomes descritivos** (Given-When-Then ou GWT):
  - ✗ `test_execute()`
  - ✓ `test_ingests_approved_document()`
  - ✓ `test_raises_conflict_when_document_already_ingested()`

## Estrutura AAA

```python
async def test_example():
    # Arrange — setup
    action = CreateConversationAction()

    # Act — ação sob teste
    conversation = await action.execute(ConversationCreateData(title="Dúvidas"))

    # Assert — verificação
    assert conversation.is_open()
```

## Executando

```bash
# Tudo
pytest

# Por camada
pytest tests/unit
pytest tests/integration
pytest tests/e2e

# Por padrão
pytest -k "document"
pytest -k "ingests and not lists"

# Com coverage
pytest --cov=src --cov-report=term-missing

# Parar no primeiro erro
pytest -x

# Paralelo (precisa pytest-xdist)
pytest -n auto
```

## Armadilhas comuns

**❌ Teste que não popula contexto**
```python
async def test_ingest_document():
    action = IngestDocumentAction(...)  # falha — CurrentAsyncSessionContext vazio
```
→ Use fixture `db_session`.

**❌ Teste que não limpa contexto entre execuções**
```python
async def test_a():
    CurrentAsyncSessionContext.set(session_a)

async def test_b():
    # session_a ainda no contexto — estado vaza
```
→ `reset_contexts` `autouse=True` resolve.

**❌ Teste sem rollback**
→ Use `db_session` fixture transacional.

**❌ Teste e2e chamando Notion/LLM de verdade**
→ Mock os clients externos.

**❌ Misturar Entity e Model em assertions**
```python
document = await repository.get_by_id(...)
assert isinstance(document, DocumentModel)  # ❌ Repository devolve Entity, não Model
```
→ Repository deve devolver Entity. Se está testando algo do Model, use a sessão direto, não o Repository.

## Checklist

- [ ] Contextos reset entre testes (fixture autouse).
- [ ] `db_session` fixture com rollback transacional.
- [ ] Clients externos (Notion/MCP, LLM) mockados.
- [ ] Repository devolve Entity (não Model) — verifique nas assertions.
- [ ] Estrutura AAA visível.
- [ ] Nome descreve comportamento.
- [ ] Sem sleep, sem dependência de ordem.
- [ ] Fakes para domínio, mocks para infra.

## Referências internas

- Convenções: `docs/conventions.md`
- Arquitetura (context vars): `docs/architecture.md`
- Database (factories detalhadas): `docs/database-guide.md`
- ADRs de contexto: `docs/adr/0006-*`

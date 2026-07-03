# Convenções de Código

Este documento define naming, estilo e padrões de código da arquitetura-alvo. Para arquitetura geral, ver `docs/architecture.md`. Para Action vs Service, ver `docs/actions-vs-services.md`.

## Princípios gerais

- **Clareza vence brevidade.** `list_approved_documents` é melhor que `list_appr_d`.
- **Consistência vence preferência pessoal.** Siga o padrão do projeto.
- **Convenção explícita é melhor que implícita.** Se um padrão não está claro, documente ou pergunte.
- **Camadas físicas refletem camadas lógicas.** A pasta diz o papel arquitetural do arquivo.
- **OOP: lógica de domínio mora em classes.** Sem funções soltas no nível do módulo para conversões, mappers, helpers que tocam tipos de domínio. Veja [Sem funções no nível do módulo](#sem-funções-no-nível-do-módulo) abaixo.

## Sem funções no nível do módulo

**Regra inegociável:** lógica relacionada a tipos de domínio (Entity, Model, DTO, Action) **mora em classes**. Não defina `def` no topo do módulo para converter, mapear ou manipular esses tipos.

### Por que

O projeto segue OOP estrita. Funções soltas no nível do módulo:

- Quebram a coesão visual da camada (uma pasta de "repositories" deve ter classes Repository, não um misto de classes e helpers procedurais).
- Tornam a discoverability pior — você espera achar `to_entity` em `DocumentMapper`, não como `_document_to_entity` perdido em algum `.py`.
- Convidam à dispersão de responsabilidades — a próxima vez vira um `_validate`, depois um `_normalize`, e o módulo deixa de ter um dono claro.

### Como aplicar

| Caso | Errado | Certo |
|---|---|---|
| Conversor Entity ↔ Model | `def _document_to_entity(model): ...` no topo do `document_repository.py` | Classe `DocumentMapper` em `src/domain/documents/mappers/document_mapper.py` com `@staticmethod to_entity(model)` |
| Helper que opera em Entity | `def is_approved(doc): ...` no topo de algum action | Método na própria Entity (`Document.is_approved()`) ou na Action que precisa |
| Cálculo derivado de DTO | `def _strip_html(data): ...` | Método estático no Repository ou na própria DTO |
| Utilitário genérico (sem domínio) | `def slugify(s): ...` no topo de um `helpers.py` | Classe utilitária em `src/support/utils/` (mesmo que tenha um único método estático) |

### Exemplos

**❌ Errado** — converter como função no topo do repository:

```python
# src/domain/documents/repositories/document_repository.py
def _document_to_entity(model: DocumentModel) -> Document:
    return Document(uuid=model.uuid, ...)

class DocumentRepository:
    async def get_by_id(self, ...):
        ...
        return _document_to_entity(model)
```

**✅ Certo** — Mapper class dedicada:

```python
# src/domain/documents/mappers/document_mapper.py
class DocumentMapper:
    @staticmethod
    def to_entity(model: "DocumentModel") -> Document:
        return Document(uuid=model.uuid, ...)

# src/domain/documents/repositories/document_repository.py
from src.domain.documents.mappers import DocumentMapper

class DocumentRepository:
    async def get_by_id(self, ...):
        ...
        return DocumentMapper.to_entity(model)
```

### Onde Mappers vivem

Cada subdomínio tem `src/domain/{ctx}/mappers/`:

```text
src/domain/documents/mappers/document_mapper.py           → DocumentMapper
src/domain/conversations/mappers/conversation_mapper.py   → ConversationMapper
```

Mapper de uma subárea pode importar Mapper de outra quando um relacionamento exige. A direção do import segue ADR-0001 (`app → domain → support`).

## Nomenclatura de arquivos e classes

### Padrão geral

- `snake_case` para arquivos Python e pastas.
- `PascalCase` para classes.
- Nome do arquivo reflete a classe principal que ele contém.

### Tabela completa

| Tipo | Pasta | Arquivo | Classe |
|---|---|---|---|
| **Entity** | `src/domain/{ctx}/entities/` | `{nome}.py` (singular) | `Document`, `Conversation` |
| **Model SQLAlchemy** | `src/domain/{ctx}/models/` | `{nome}.py` (singular) | `DocumentModel`, `ConversationModel` |
| **Action** | `src/domain/{ctx}/actions/` | `{verbo}_{substantivo}_action.py` | `IngestDocumentAction` |
| **Domain Service** | `src/domain/{ctx}/services/` | `{nome}_service.py` | `ContentSanitizerService` |
| **Repository** | `src/domain/{ctx}/repositories/` | `{nome}_repository.py` | `DocumentRepository` |
| **Mapper** | `src/domain/{ctx}/mappers/` | `{nome}_mapper.py` | `DocumentMapper` |
| **DTO** | `src/domain/{ctx}/dtos/` | `{nome}_data.py` | `DocumentIngestData`, `DocumentUpdateData` |
| **Enum** | `src/domain/{ctx}/enums/` | `{nome}_enum.py` | `DocumentStatusEnum` |
| **Value Object** | `src/domain/shared/value_objects/` | `{nome}.py` | `SourceUrl`, `Citation` |
| **Controller** | `src/app/api/controllers/` | `{dominio}_controller.py` | `DocumentController` |
| **Request schema** | `src/app/api/requests/` | `{dominio}_requests.py` ou `{nome}_request.py` | `IngestDocumentRequest` |
| **Response schema** | `src/app/api/responses/` | `{dominio}_responses.py` ou `{nome}_response.py` | `DocumentResponse` |
| **Middleware** | `src/app/api/middlewares/` | `{nome}_middleware.py` | `DBSessionMiddleware` |
| **Dependency** | `src/app/api/dependencies/` | `{nome}.py` | função (ex.: futura `require_authenticated`) |
| **Route** | `src/app/api/routes/` | `{dominio}.py` (plural) | variável `router` |
| **Job** | `src/app/console/jobs/` | `{nome}_job.py` | `SyncKnowledgeBaseJob` |
| **CLI Command** | `src/app/console/commands/` | `{nome}_command.py` | `DocumentsIngestCommand` |
| **Client** | `src/support/clients/` | `{nome}_client.py` | `NotionClient` |
| **Mixin** | `src/support/core/mixins/` | `{caracteristica}.py` | `HasUUID`, `HasTimestamps` |
| **Util** | `src/support/utils/` | `{nome}.py` | função/classe |
| **ContextVar** | `src/support/core/context/` | `current_{nome}_context.py` | `CurrentRequestContext` |
| **Exception** | `src/support/core/exceptions.py` (arquivo único) | — | `DomainError`, `NotFoundError` |
| **Seed** | `database/seeds/` | `{nome}_seed.py` | `DocumentSourcesSeed` |
| **Factory** | `database/factories/` | `{nome}_factory.py` | `DocumentFactory` |

### Sufixos importantes

- **Entity** — sem sufixo. `Document`, `Conversation`.
- **Model** — sufixo `Model` para diferenciar da Entity. `DocumentModel`, `ConversationModel`.
- **Action** — sufixo `Action`. `IngestDocumentAction`.
- **Service** — sufixo `Service` (Domain Services apenas, não facade). `ContentSanitizerService`.
- **Repository** — sufixo `Repository`. `DocumentRepository`.
- **Mapper** — sufixo `Mapper`. `DocumentMapper`, `ConversationMapper`.
- **Controller** — sufixo `Controller`. `DocumentController`.

## Nomenclatura de variáveis e funções

- **`snake_case`** para funções e variáveis.
- **Booleanos com prefixo:** `is_`, `has_`, `can_`, `should_`. Exemplos: `is_approved`, `has_content`, `can_index`.
- **Evite abreviações:** `document` não `doc`, `repository` não `repo` (exceto localmente em expressões curtas).
- **Constantes em `UPPER_SNAKE_CASE`** em escopo de módulo.

### Métodos de repositório — convenção importante

| Padrão | Retorno | Exemplo |
|---|---|---|
| `get_by_*` | `Optional[Entity]` (não lança) | `get_by_id`, `get_by_notion_page_id` |
| `list_*` | `list[Entity]` | `list_documents`, `list_approved_documents` |
| `validate_*_exists` | `bool` | `validate_source_exists` |
| `create` | `Entity` | `create` |
| `update` | `Entity` | `update` |
| `sync_*` | `list[Entity]` ou Entity atualizada | `sync_from_notion` |

**Lembre:** `get_by_*` retorna `Optional` (não lança). Lançar exceção é responsabilidade da Action.

## Entities (domínio puro)

```python
# src/domain/documents/entities/document.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Document:
    """Documento da base de conhecimento."""
    uuid: UUID
    notion_page_id: str
    title: str
    content: str
    source_url: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_approved(self) -> bool:
        return self.status == "approved" and self.deleted_at is None
```

**Regras:**
- `@dataclass` puro. `frozen=True` se imutável.
- **Sem** `import sqlalchemy`, **sem** `import fastapi`, **sem** `import pydantic`.
- Pode ter métodos de comportamento simples.
- Tipos modernos Python 3.13+: `UUID | None`, `list[Citation]`.
- Relacionamentos como `list[OutraEntity]` ou `OutraEntity | None`.

## Models (SQLAlchemy puro)

```python
# src/domain/documents/models/document.py
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.models.base_model import BaseModel
from src.support.core.mixins import HasUUID, HasTimestamps, ApplyRelations


class DocumentModel(BaseModel, HasUUID, HasTimestamps, ApplyRelations):
    __tablename__ = "documents"

    notion_page_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(20), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

### Mixins padrão

A combinação típica para entidade de negócio:

```python
class FooModel(BaseModel, HasUUID, HasTimestamps, ApplyRelations):
    ...
```

- **`BaseModel`** (`src/support/core/models/base_model.py`) — `DeclarativeBase` compartilhado. **Sempre primeiro.**
- **`HasUUID`** — PK UUID v7 via `uuid6.uuid7`. Campo `uuid`.
- **`HasTimestamps`** — `created_at`, `updated_at` com server defaults.
- **`ApplyRelations`** — classmethod para eager load dinâmico por dot-notation.

### Soft delete

Convenção (não mixin): campo `deleted_at: datetime | None`. Repositories filtram manualmente:

```python
query = select(DocumentModel).where(DocumentModel.deleted_at.is_(None))
```

Para incluir deletados, parâmetro `with_trashed: bool = False` no método.

### Relacionamentos

```python
messages: Mapped[list["MessageModel"]] = relationship(
    back_populates="conversation",
    lazy="selectin",
)
```

Preferência: `lazy='selectin'` para relacionamentos carregados frequentemente. Use `lazy='joined'` apenas quando 1-to-1 e sempre necessário.

## DTOs (cruzam camadas)

```python
# src/domain/documents/dtos/document_data.py
from dataclasses import dataclass


@dataclass
class DocumentIngestData:
    notion_page_id: str


@dataclass
class DocumentUpdateData:
    title: str | None = None
    content: str | None = None
    status: str | None = None
```

**Regras:**
- DTOs internos do domínio são `@dataclass`, não Pydantic.
- Sufixo `Data` no nome.
- Conservadores: só os campos necessários para a operação.
- DTOs de **request/response** são Pydantic e ficam em `src/app/api/`, não aqui.

## Repositories

```python
# src/domain/documents/repositories/document_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from src.support.core.context import CurrentAsyncSessionContext
from src.domain.documents.entities.document import Document
from src.domain.documents.mappers import DocumentMapper
from src.domain.documents.models.document import DocumentModel


class DocumentRepository:
    def __init__(self):
        self.session = CurrentAsyncSessionContext.get()
        if not self.session:
            raise RuntimeError("No active database session found in context.")

    async def get_by_id(self, document_id: UUID, with_trashed: bool = False) -> Optional[Document]:
        query = select(DocumentModel).where(DocumentModel.uuid == document_id)
        if not with_trashed:
            query = query.where(DocumentModel.deleted_at.is_(None))

        result = await self.session.execute(query)
        model = result.unique().scalar_one_or_none()
        return DocumentMapper.to_entity(model) if model else None

    async def create(self, document: Document) -> Document:
        model = DocumentModel(**DocumentMapper.to_model_attrs(document))
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return DocumentMapper.to_entity(model)
```

**Regras:**
- **Session do contexto**, não injetada.
- **API pública fala em Entities**, não Models.
- **Conversão Entity ↔ Model fica no Mapper** (`src/domain/{ctx}/mappers/`), não inline no Repository.
- Não comita.
- `result.unique().scalar_one_or_none()` para `get_by_*`.
- `result.unique().scalars().all()` para `list_*`.

## Actions

```python
# src/domain/documents/actions/ingest_document_action.py
from src.domain.documents.entities.document import Document
from src.domain.documents.repositories.document_repository import DocumentRepository
from src.domain.documents.dtos.document_data import DocumentIngestData
from src.support.clients.notion.notion_client import NotionClient
from src.support.core.exceptions import DomainConflictError


class IngestDocumentAction:
    """Ingere um documento aprovado do Notion na base de conhecimento."""

    def __init__(self, notion_client: NotionClient):
        self.repository = DocumentRepository()
        self.notion = notion_client

    async def execute(self, data: DocumentIngestData) -> Document:
        existing = await self.repository.get_by_notion_page_id(data.notion_page_id)
        if existing:
            raise DomainConflictError(f"Documento {data.notion_page_id} já foi ingerido")
        # ... lógica
```

**Regras:**
- Sufixo **`Action`**.
- Método público único: `execute()`.
- `__init__` recebe Clients e outras Actions.
- Repository instanciado direto (pega session do contexto).
- Recebe DTOs ou primitivos. Retorna Entity.
- **Lança exceções de domínio**, nunca `HTTPException`.
- Helpers privados com `_`.
- Docstring curta.

## Controllers

```python
# src/app/api/controllers/document_controller.py
from fastapi import Request

from src.app.api.requests.document_requests import IngestDocumentRequest
from src.app.api.responses.document_responses import DocumentResponse
from src.support.clients.notion.notion_client import NotionClient
from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.dtos.document_data import DocumentIngestData


class DocumentController:
    @staticmethod
    async def ingest_document(request: Request, payload: IngestDocumentRequest):
        action = IngestDocumentAction(notion_client=NotionClient())
        document = await action.execute(DocumentIngestData(
            notion_page_id=payload.notion_page_id,
        ))
        return DocumentResponse.from_entity(document)
```

**Regras:**
- Todos os métodos `@staticmethod`.
- **Não tem regra de negócio** — extrai dados, chama Action, devolve Response.
- Não chama Repository diretamente.
- Sem `try/except` — exception_handlers no `main.py` cuidam disso.

## Request schemas (Pydantic)

```python
# src/app/api/requests/document_requests.py
from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    notion_page_id: str = Field(min_length=1)


class UpdateDocumentRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
```

## Response schemas (Pydantic)

```python
# src/app/api/responses/document_responses.py
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from src.domain.documents.entities.document import Document


class DocumentResponse(BaseModel):
    uuid: UUID
    title: str
    source_url: str
    status: str
    is_approved: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, document: Document) -> "DocumentResponse":
        return cls(
            uuid=document.uuid,
            title=document.title,
            source_url=document.source_url,
            status=document.status,
            is_approved=document.is_approved(),
            created_at=document.created_at,
        )


class DocumentListResponse(BaseModel):
    """Versão resumida para listas"""
    uuid: UUID
    title: str
    status: str

    @classmethod
    def from_entity(cls, document: Document) -> "DocumentListResponse":
        return cls(uuid=document.uuid, title=document.title, status=document.status)
```

**Regras:**
- Método `from_entity` (singular) ou `from_entities` (plural) para conversão.
- Schemas de listagem podem ser mais resumidos que os de detalhe.

## Rotas

```python
# src/app/api/routes/documents.py
from fastapi import APIRouter

from src.app.api.controllers.document_controller import DocumentController


router = APIRouter(prefix="/documents", tags=["Documents"])
# Auth: ponto em aberto. Quando definida, entra como dependency do router:
#   router = APIRouter(..., dependencies=[Depends(require_authenticated)])

router.get("")(DocumentController.list_documents)
router.post("")(DocumentController.ingest_document)
router.get("/{document_id}")(DocumentController.get_document)
router.put("/{document_id}")(DocumentController.update_document)
router.delete("/{document_id}")(DocumentController.archive_document)
```

**Regras:**
- **Mapeamento via chamada**, não decorador.
- **Prefix e tags** no `APIRouter(...)`.
- **Dependências de auth** (quando existirem) no router, não em cada rota.
- **Arquivo plural** (`documents.py`).
- Variável `router` (padrão) ou `public_router` (explicitamente sem auth).
- Autodiscovery cuida do registro.

## Jobs

```python
# src/app/console/jobs/sync_knowledge_base_job.py
from src.support.core.scheduling import Job
import logging

logger = logging.getLogger(__name__)


class SyncKnowledgeBaseJob(Job):
    """Sincroniza documentos aprovados do Notion."""

    min_execution_interval = 60  # opcional

    async def action(self):
        # idempotente
        ...
```

Registro em `src/app/console/schedule.py`:

```python
schedule.call(SyncKnowledgeBaseJob).hourly()
```

## Estilo Python

### Tipos modernos

Python 3.13+:

```python
# ✓ Bom
def find_document(id: UUID) -> Document | None: ...
def list_documents() -> list[Document]: ...

# ✗ Evitar
from typing import Optional, List
def find_document(id: UUID) -> Optional[Document]: ...
```

### Imports

**Sempre absolutos**, partindo de `src/`:

```python
from src.domain.documents.entities.document import Document
from src.support.core.context import CurrentAsyncSessionContext
```

**Ordem:**
1. Standard library
2. Third-party
3. Projeto (`from src.app...`, `from src.domain...`, `from src.support...`)

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Document ingested: %s", document.uuid)
logger.error("Failed to ingest document", exc_info=True)
```

Formato com `%s`, não f-string — permite lazy evaluation.

### Docstrings

- **Classes Action/Service/Repository:** docstring curta.
- **Métodos públicos complexos:** Args/Returns/Raises se não óbvio.
- **Funções triviais:** dispensam.

```python
async def execute(self, data: DocumentIngestData) -> Document:
    """
    Ingere um documento aprovado do Notion na base de conhecimento.

    Args:
        data: Referência do documento a ingerir.

    Returns:
        Entity Document com UUID gerado.

    Raises:
        DomainConflictError: Se o documento já tiver sido ingerido.
    """
```

## Checklist antes de commit

- [ ] Lint passa (`prospector`).
- [ ] Type hints em funções públicas.
- [ ] Imports absolutos partindo de `src/`.
- [ ] Sem `print`, sem código comentado.
- [ ] Entity sem importar SQLAlchemy/FastAPI/Pydantic.
- [ ] Action lança exceção de domínio, não HTTPException.
- [ ] Controller é fino — sem regra de negócio.
- [ ] Repository pega session do contexto.
- [ ] Model novo herda mixins corretos.
- [ ] Rota nova em `src/app/api/routes/`.
- [ ] Sem violação das regras inegociáveis do `CLAUDE.md`.

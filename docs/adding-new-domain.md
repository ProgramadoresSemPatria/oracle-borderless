# Adicionando um Novo Subdomínio

Checklist passo a passo para criar um subdomínio novo (ex: `conversations`, `feedbacks`, `sources`) na arquitetura-alvo.

Para arquitetura geral, ver `docs/architecture.md`. Para distinção Action vs Service, ver `docs/actions-vs-services.md`.

> **Atalho:** `python cli.py make:domain {nome}` automatiza ~90% deste guia (Passos 1, 2, 3, 5, 6, 7, 9, 10 num único comando). Veja `docs/scaffolding-guide.md`. Use o checklist abaixo quando precisar fazer manualmente, entender o porquê de cada peça, ou ajustar algo que o gerador não cobre (Passos 4 — Migration, 8 — Request/Response, 11 — Seed, 12 — Job, 13 — Factory, 14 — Testes).

## Antes de começar — é realmente um subdomínio novo?

Nem toda feature merece subdomínio. Pergunte:

- **Tem vocabulário de negócio próprio?** "Conversa", "mensagem", "resposta" são vocabulário que `documents` não tem.
- **Tem ciclo de vida independente?** Uma conversa tem estados próprios (aberta, encerrada).
- **Pode evoluir sozinho?** Mudar regras de conversação não deveria afetar a base de conhecimento.

Se respondeu "não" às três, está **estendendo** um subdomínio existente:

- Action nova → arquivo em `src/domain/{ctx}/actions/{verbo}_{substantivo}_action.py`.
- Endpoint novo → método em controller existente + linha em `src/app/api/routes/{ctx}.py`.
- Campo novo em entidade → ajusta Entity + Model + migration.

**Casos típicos que NÃO são subdomínio novo:**
- Novo filtro de listagem de documentos → Action em `documents`.
- Campo `language` no documento → ajusta Entity/Model `Document` + migration.
- Validação nova na ingestão → ajusta `IngestDocumentAction`.

**Casos típicos que SÃO subdomínio novo:**
- Conversas do oráculo (perguntas/respostas) → `conversations`.
- Feedback dos usuários sobre respostas → `feedbacks`.
- Catálogo de fontes além do Notion → `sources`.

## Estrutura a criar

```
src/domain/{contexto}/
├── __init__.py
├── entities/
│   ├── __init__.py
│   └── {entidade}.py
├── models/
│   ├── __init__.py
│   └── {entidade}.py
├── actions/
│   ├── __init__.py
│   ├── create_{entidade}_action.py
│   ├── list_{entidade}s_action.py
│   └── ...
├── services/                    # opcional, geralmente vazio inicialmente
│   └── __init__.py
├── repositories/
│   ├── __init__.py
│   └── {entidade}_repository.py
├── mappers/
│   ├── __init__.py
│   └── {entidade}_mapper.py
├── dtos/
│   ├── __init__.py
│   └── {entidade}_data.py
└── enums/                       # se aplicável
    ├── __init__.py
    └── {nome}_enum.py
```

## Passo 1 — Entity (domínio puro)

```python
# src/domain/conversations/entities/conversation.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Conversation:
    """Conversa do oráculo — sequência de perguntas e respostas."""
    uuid: UUID
    title: str
    status: str            # "open" | "closed"
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_open(self) -> bool:
        return self.status == "open" and self.deleted_at is None

    def is_closed(self) -> bool:
        return self.status == "closed"
```

**Regras:**
- `@dataclass` puro.
- Sem `import sqlalchemy`, `import fastapi`, `import pydantic`.
- Métodos de comportamento simples vão aqui.

## Passo 2 — Model (SQLAlchemy puro)

```python
# src/domain/conversations/models/conversation.py
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.models.base_model import BaseModel
from src.support.core.mixins import HasUUID, HasTimestamps, ApplyRelations


class ConversationModel(BaseModel, HasUUID, HasTimestamps, ApplyRelations):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

**Lembre:**
- Sufixo **`Model`** no nome.
- Mixins padrão: `BaseModel, HasUUID, HasTimestamps, ApplyRelations`.
- `uuid`, `created_at`, `updated_at` vêm dos mixins.
- Soft delete: `deleted_at: datetime | None`.
- **Sem método de negócio** — comportamento mora na Entity.

## Passo 3 — Registrar no `models/__init__.py` do subdomínio

```python
# src/domain/conversations/models/__init__.py
from .conversation import ConversationModel

__all__ = ["ConversationModel"]
```

E garantir que `database/env.py` importa o módulo (necessário para `alembic --autogenerate` enxergar):

```python
# database/env.py
from src.domain.conversations.models import *  # ou import explícito
```

## Passo 4 — Migration

```bash
alembic revision --autogenerate -m "create conversations table"
```

**Revise o arquivo gerado.** Confira:
- Nome da tabela.
- Colunas e tipos (especialmente `DateTime`).
- Foreign keys com `ondelete` correto.
- Índices declarados no model.

```bash
alembic upgrade head
```

## Passo 5 — DTOs internos

```python
# src/domain/conversations/dtos/conversation_data.py
from dataclasses import dataclass


@dataclass
class ConversationCreateData:
    title: str


@dataclass
class ConversationUpdateData:
    status: str
```

**Regras:**
- DTOs internos do domínio são **dataclasses**, não Pydantic.
- Sufixo `Data`.
- Conservadores: só campos necessários.

## Passo 6 — Mapper + Repository

A conversão Entity ↔ Model fica num **Mapper** dedicado (`src/domain/{ctx}/mappers/`). O Repository delega ao Mapper na fronteira pública — não implementa conversão inline.

### Mapper

```python
# src/domain/conversations/mappers/conversation_mapper.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.conversations.entities.conversation import Conversation

if TYPE_CHECKING:
    from src.domain.conversations.models.conversation import ConversationModel


class ConversationMapper:
    @staticmethod
    def to_entity(model: "ConversationModel") -> Conversation:
        return Conversation(
            uuid=model.uuid,
            title=model.title,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model_attrs(entity: Conversation) -> dict:
        """Atributos como dict para passar a `ConversationModel(**attrs)` ou `update().values(**attrs)`."""
        return {
            "uuid": entity.uuid,
            "title": entity.title,
            "status": entity.status,
        }
```

**Padrões:**
- Sufixo **`Mapper`**.
- Métodos `@staticmethod` — sem estado.
- `to_entity(model) -> Entity`. Para escrita, `to_model_attrs(entity) -> dict`.
- Mapper pode importar Mapper de outro subdomínio quando um relacionamento exige. Direção segue ADR-0001.

### Repository

```python
# src/domain/conversations/repositories/conversation_repository.py
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from src.support.core.context import CurrentAsyncSessionContext
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.mappers.conversation_mapper import ConversationMapper
from src.domain.conversations.models.conversation import ConversationModel


class ConversationRepository:
    def __init__(self):
        self.session = CurrentAsyncSessionContext.get()
        if not self.session:
            raise RuntimeError("No active database session found in context.")

    async def get_by_id(
        self,
        conversation_id: UUID,
        with_trashed: bool = False,
    ) -> Optional[Conversation]:
        query = select(ConversationModel).where(ConversationModel.uuid == conversation_id)
        if not with_trashed:
            query = query.where(ConversationModel.deleted_at.is_(None))

        result = await self.session.execute(query)
        model = result.unique().scalar_one_or_none()
        return ConversationMapper.to_entity(model) if model else None

    async def list_conversations(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Conversation]:
        query = (
            select(ConversationModel)
            .where(ConversationModel.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(ConversationModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return [ConversationMapper.to_entity(m) for m in result.unique().scalars().all()]

    async def create(self, conversation: Conversation) -> Conversation:
        model = ConversationModel(**ConversationMapper.to_model_attrs(conversation))
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return ConversationMapper.to_entity(model)
```

**Padrões:**
- Session do contexto, não injetada.
- API pública fala em **Entities**.
- **Conversão Entity ↔ Model fica no Mapper**, não inline.
- `get_by_*` retorna `Optional` (não lança).
- `list_*` retorna `list` (pode ser vazia).
- Não comita.

## Passo 7 — Actions

Cada caso de uso é uma Action separada.

### CreateConversationAction

```python
# src/domain/conversations/actions/create_conversation_action.py
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.dtos.conversation_data import ConversationCreateData
from src.support.core.exceptions import ValidationError


class CreateConversationAction:
    """Inicia uma nova conversa com o oráculo."""

    def __init__(self):
        self.repository = ConversationRepository()

    async def execute(self, data: ConversationCreateData) -> Conversation:
        if not data.title.strip():
            raise ValidationError("Título da conversa é obrigatório")

        conversation = Conversation(
            uuid=None,          # gerado pelo HasUUID no insert
            title=data.title,
            status="open",
            created_at=None,
            updated_at=None,
        )
        return await self.repository.create(conversation)
```

### ListConversationsAction

```python
# src/domain/conversations/actions/list_conversations_action.py
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository


class ListConversationsAction:
    def __init__(self):
        self.repository = ConversationRepository()

    async def execute(self, skip: int = 0, limit: int = 100) -> list[Conversation]:
        return await self.repository.list_conversations(skip=skip, limit=limit)
```

**Regras:**
- Sufixo **`Action`**.
- Método público único: `execute()`.
- Recebe DTO ou primitivos. Retorna Entity.
- Lança exceções de domínio (`src/support/core/exceptions.py`), nunca `HTTPException`.
- Repository instanciado direto.

## Passo 8 — Request/Response schemas (Pydantic)

### Request

```python
# src/app/api/requests/conversation_requests.py
from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
```

### Response

```python
# src/app/api/responses/conversation_responses.py
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from src.domain.conversations.entities.conversation import Conversation


class ConversationResponse(BaseModel):
    uuid: UUID
    title: str
    status: str
    is_open: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, conversation: Conversation) -> "ConversationResponse":
        return cls(
            uuid=conversation.uuid,
            title=conversation.title,
            status=conversation.status,
            is_open=conversation.is_open(),
            created_at=conversation.created_at,
        )
```

## Passo 9 — Controller

```python
# src/app/api/controllers/conversation_controller.py
from fastapi import Request

from src.app.api.requests.conversation_requests import CreateConversationRequest
from src.app.api.responses.conversation_responses import ConversationResponse
from src.domain.conversations.actions.create_conversation_action import CreateConversationAction
from src.domain.conversations.actions.list_conversations_action import ListConversationsAction
from src.domain.conversations.dtos.conversation_data import ConversationCreateData


class ConversationController:
    @staticmethod
    async def list_conversations(request: Request, skip: int = 0, limit: int = 100):
        action = ListConversationsAction()
        conversations = await action.execute(skip=skip, limit=limit)
        return [ConversationResponse.from_entity(c) for c in conversations]

    @staticmethod
    async def create_conversation(request: Request, payload: CreateConversationRequest):
        action = CreateConversationAction()
        conversation = await action.execute(ConversationCreateData(title=payload.title))
        return ConversationResponse.from_entity(conversation)
```

**Regras:**
- `@staticmethod`.
- Não tem regra de negócio.
- Não chama Repository diretamente.
- Converte Request em DTO, chama Action, devolve Response.

## Passo 10 — Rota (autodiscovery faz o resto)

```python
# src/app/api/routes/conversations.py
from fastapi import APIRouter

from src.app.api.controllers.conversation_controller import ConversationController


router = APIRouter(prefix="/conversations", tags=["Conversations"])
# Auth: ponto em aberto. Quando definida, entra como dependency do router:
#   router = APIRouter(..., dependencies=[Depends(require_authenticated)])

router.get("")(ConversationController.list_conversations)
router.post("")(ConversationController.create_conversation)
router.get("/{conversation_id}")(ConversationController.get_conversation)
```

**Pronto — não precisa registrar em lugar nenhum.** Autodiscovery em `src/app/api/routes/__init__.py` detecta.

Para rotas **explicitamente públicas** (sem a futura auth), use `public_router`:

```python
public_router = APIRouter(prefix="/public-stuff", tags=["Public"])
public_router.get("/health")(HealthController.check)
```

## Passo 11 — Seed inicial (se houver dados base)

```python
# database/seeds/document_sources_seed.py
from src.domain.sources.actions.create_source_action import CreateSourceAction
from src.domain.sources.repositories.source_repository import SourceRepository


class DocumentSourcesSeed:
    DATA = [
        {"key": "notion", "name": "Notion (MCP)"},
    ]

    @staticmethod
    async def seed():
        repository = SourceRepository()
        action = CreateSourceAction()

        for data in DocumentSourcesSeed.DATA:
            existing = await repository.get_by_key(data["key"])
            if existing is None:
                await action.execute(key=data["key"], name=data["name"])
```

Registrar em `database/seeds/__init__.py` (ver `docs/database-guide.md`).

## Passo 12 — Job agendado (se houver)

```python
# src/app/console/jobs/close_stale_conversations_job.py
from src.support.core.scheduling import Job
from src.domain.conversations.actions.close_stale_conversations_action import CloseStaleConversationsAction


class CloseStaleConversationsJob(Job):
    """Encerra conversas abertas há mais de 24h sem atividade."""

    min_execution_interval = 60

    async def action(self):
        # Job é wrapper fino — delega para Action
        action = CloseStaleConversationsAction()
        await action.execute()
```

Registrar em `src/app/console/schedule.py`:

```python
schedule.call(CloseStaleConversationsJob).hourly()
```

**Padrão:** Jobs são wrappers finos. A lógica vive na Action — assim pode ser reusada via CLI, HTTP.

## Passo 13 — Factory para testes

```python
# database/factories/conversation_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.domain.conversations.models.conversation import ConversationModel


class ConversationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ConversationModel
        sqlalchemy_session_persistence = "flush"

    title = factory.Faker("sentence", nb_words=4)
    status = "open"
```

## Passo 14 — Testes

```
tests/
├── unit/
│   └── domain/
│       └── conversations/
│           ├── entities/
│           │   └── test_conversation.py
│           └── actions/
│               ├── test_create_conversation_action.py
│               └── test_list_conversations_action.py
├── integration/
│   └── domain/
│       └── conversations/
│           └── repositories/
│               └── test_conversation_repository.py
└── e2e/
    └── api/
        └── test_conversation_endpoints.py
```

Padrões em **`docs/testing-guide.md`** (especialmente sobre context vars e fixtures).

## Checklist final

- [ ] Entity em `src/domain/{ctx}/entities/` — dataclass pura.
- [ ] Model em `src/domain/{ctx}/models/` — SQLAlchemy + mixins.
- [ ] Model registrado em `src/domain/{ctx}/models/__init__.py`.
- [ ] Migration gerada, revisada, aplicada.
- [ ] DTOs em `src/domain/{ctx}/dtos/` — dataclasses.
- [ ] Mapper em `src/domain/{ctx}/mappers/` — `to_entity` + `to_model_attrs`.
- [ ] Repository com session do contexto, delegando conversão Entity ↔ Model ao Mapper.
- [ ] Actions em `src/domain/{ctx}/actions/` — uma por caso de uso.
- [ ] Request/Response Pydantic em `src/app/api/`.
- [ ] Controller fino em `src/app/api/controllers/`.
- [ ] Rota em `src/app/api/routes/{ctx}.py`.
- [ ] Seeds criadas e registradas (se houver dados base).
- [ ] Factory em `database/factories/` (se entidade central).
- [ ] Jobs em `src/app/console/jobs/` + registrados em `schedule.py` (se houver periódicos).
- [ ] Testes unitários para Entity (comportamento) e Actions.
- [ ] Testes integração para Repository.
- [ ] Testes e2e para fluxos críticos.
- [ ] ADR registrado se houver decisões arquiteturais relevantes.

## Em caso de dúvida

Padrões divergentes espalhados por subdomínios corroem a arquitetura rápido. Se um passo não couber neste fluxo (ex: subdomínio com workflow complexo, integração externa nova), **pergunte antes de inventar**.

# Guia de Database

Este guia cobre como lidar com o banco na arquitetura-alvo: **dual engine**, **migrations**, **seeds com tracking** e **factories**. Para arquitetura geral, ver `docs/architecture.md`.

## Estrutura

```
database/                            # FORA de src/
├── env.py                           # config Alembic
├── script.py.mako                   # template de migrations
├── README
├── migrations/
│   └── YYYY_MM_DD_HHMMSS-{rev}_{descrição}.py
├── seeds/                           # dados ESSENCIAIS (prod-safe)
│   ├── __init__.py                  # run_all_seeders + tracking
│   ├── __main__.py
│   ├── document_sources_seed.py
│   └── dev_documents_seed.py        # só ENVIRONMENT=development
└── factories/                       # dados FAKE (dev/test)
    ├── __init__.py
    ├── document_factory.py
    └── conversation_factory.py
```

`database/` fica **fora** de `src/`. É infraestrutura de dados com ciclo de vida próprio — migrations versionadas, seeds idempotentes, factories de teste.

**Distinção fundamental seeds vs factories:**

- **Seeds** (`database/seeds/`): dados **essenciais e reais** que a aplicação precisa em qualquer ambiente — ex.: catálogo de fontes. Idempotentes, com tracking.
- **Factories** (`database/factories/`): geradores de dados **fake e abundantes** para desenvolvimento e testes — não vão para produção.

## Dual engine — async + sync

Aplicação usa **dois engines SQLAlchemy paralelos**, configurados em `src/support/core/database.py`.

### Async (asyncpg) — padrão

```python
engine = create_async_engine(
    get_database_url_async(),
    pool_size=settings.DB_POOL_SIZE,
    pool_pre_ping=True,
    connect_args={"server_settings": {"timezone": "UTC"}},
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

Usado em todo código HTTP, seeds e na maior parte dos jobs.

### Sync (psycopg) — específico

```python
sync_engine = create_engine(
    get_database_url_sync(),
    pool_size=settings.DB_POOL_SIZE,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=sync_engine, ...)
```

Usado em:
- **APScheduler** — `SQLAlchemyJobStore` exige conexão síncrona (por isso o dual engine é preservado).
- **Scripts** que preferem API síncrona (raro).

### Session por request

`DBSessionMiddleware` (`src/app/api/middlewares/db_session_middleware.py`) abre sessão async e factory sync **lazy**:

```python
async with AsyncSessionLocal() as async_session:
    CurrentAsyncSessionContext.set(async_session)
    CurrentSessionContext.set_factory(SessionLocal)

    try:
        response = await call_next(request)
        await async_session.commit()
        sync_session = CurrentSessionContext.get()
        if sync_session is not None:
            sync_session.commit()
    except Exception:
        await async_session.rollback()
        ...
        raise
    finally:
        ...
```

**Implicações:**
- Repositórios **nunca criam sessão** — acessam `CurrentAsyncSessionContext.get()`.
- Sessão sync é **lazy** — só cria se alguém chamar `CurrentSessionContext.get()`.
- Commit/rollback acontece no fim da request, automaticamente. **Não comitar em Action.**
- Em jobs/seeds (fora de request), abra `AsyncSessionLocal()` manualmente e popule o contexto.

Detalhes em **ADR-0006**.

## Migrations (Alembic)

### Configuração

`database/env.py` usa `BaseModel.metadata` como target:

```python
from src.domain.documents.models import *
from src.domain.conversations.models import *
# (ou autodescoberta de imports)

from src.support.core.models.base_model import BaseModel
from src.support.core.database import engine

target_metadata = BaseModel.metadata
```

**Importante:** a tabela `apscheduler_jobs` é **excluída** do autogenerate via `include_object`, pois é gerenciada pelo próprio APScheduler. Se `alembic revision --autogenerate` mostrá-la, há problema na config.

### Convenções de nome

Formato: `YYYY_MM_DD_HHMMSS-{revision}_{descrição}.py`

```
2026_03_11_210659-26cd0dfd3eac_create_documents_table.py
2026_05_22_150340-7a8b9c0d1e2f_add_language_to_documents.py
```

**Mensagens:** imperativo curto em snake_case — `create_X_table`, `add_X_to_Y`, `remove_X_index`.

### Criando migrations

```bash
# Mudou um model?
alembic revision --autogenerate -m "add language to documents"

# Mudanças manuais (índice, extensão)?
alembic revision -m "enable uuid_ossp extension"
```

**Sempre revise o arquivo gerado.** Autogenerate:
- Trata renames como drop + create (destrutivo).
- Pode errar em enums customizados.
- Pode gerar drop_column de colunas que você apenas renomeou.

### Comandos

```bash
alembic upgrade head            # aplicar pendentes
alembic downgrade -1            # reverter última
alembic downgrade base          # reverte tudo
alembic downgrade {rev}         # reverter para revisão
alembic history
alembic current
alembic check                   # drift entre models e banco
alembic upgrade head --sql      # gerar SQL sem aplicar
```

### Produção — regras de ouro

1. **Compatibilidade durante rolling deploy.** Migration deve ser compatível com a versão **anterior** do código.
2. **Mudanças destrutivas em duas etapas.**
   - Release N: adiciona nova coluna, código escreve em ambas.
   - Release N+1: remove coluna antiga após confirmação.
3. **Migrations de dados grandes fora do Alembic.** Job dedicado ou script, não migration bloqueante. (Reingestão da base de conhecimento é caso típico — use um Job, não migration.)
4. **Índices com `CONCURRENTLY` no Postgres** para tabelas grandes — não bloqueia escrita. Não roda em transação, exige ajuste na migration.

## Seeds com tracking

### Conceito

Seeds populam **dados essenciais** que a aplicação precisa em qualquer ambiente. Têm sistema próprio de **tracking** que garante idempotência.

### Como funciona

`database/seeds/__init__.py`:

```python
async def run_all_seeders():
    async with AsyncSessionLocal() as session:
        CurrentAsyncSessionContext.set(session)

        seeders = [
            DocumentSourcesSeed,
        ]

        if settings.ENVIRONMENT == "development":
            seeders.extend([DevDocumentsSeed])

        for seeder in seeders:
            seed_name = seeder.__name__

            if await is_seed_executed(session, seed_name):
                print(f"⏭️  Skipping {seed_name}")
                continue

            await seeder.seed()
            await mark_seed_executed(session, seed_name)
```

A tabela `seeds_executions` armazena nome de cada seed já rodada. Já rodou? Pula.

### Criando uma seed nova

**1. Arquivo em `database/seeds/{nome}_seed.py`:**

```python
# database/seeds/document_sources_seed.py
from src.domain.sources.actions.create_source_action import CreateSourceAction
from src.domain.sources.repositories.source_repository import SourceRepository


class DocumentSourcesSeed:
    """Popula o catálogo de fontes de conhecimento (ex.: Notion)."""

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

**Regras:**
- Método `@staticmethod async def seed()`.
- **Idempotente** internamente (checar antes de inserir). Tracking previne re-execução, mas defesa em profundidade ajuda.
- **Use Actions, não Repository direto** — preserva regras de negócio (validações, eventos de domínio).
- Docstring explicando o que popula.

**2. Adicionar à lista em `database/seeds/__init__.py`:**

```python
from .document_sources_seed import DocumentSourcesSeed

seeders = [
    DocumentSourcesSeed,       # ← na ordem correta de dependência
]
```

**3. Rodar:**

```bash
python -m database.seeds
```

### Seeds dev-only

```python
if settings.ENVIRONMENT == "development":
    from .dev_documents_seed import DevDocumentsSeed
    seeders.append(DevDocumentsSeed)
```

Também são **tracked** — rodando duas vezes, pula da segunda em diante.

## Factories (factory-boy)

Factories geram **dados fake abundantes** para desenvolvimento e testes. **Nunca** vão para produção.

### Setup

```bash
uv add --dev factory-boy
```

### Estrutura

```
database/factories/
├── __init__.py
├── document_factory.py
└── conversation_factory.py
```

### Criando uma factory

```python
# database/factories/document_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

from src.domain.documents.models.document import DocumentModel


class DocumentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = DocumentModel
        sqlalchemy_session_persistence = "flush"   # não comita

    notion_page_id = factory.Faker("uuid4")
    title = factory.Faker("sentence", nb_words=5)
    content = factory.Faker("paragraph")
    source_url = factory.Faker("url")
    status = "approved"
```

### Uso em testes

```python
# tests/integration/test_document_repository.py
async def test_lists_documents(db_session):
    DocumentFactory._meta.sqlalchemy_session = db_session

    await DocumentFactory.create_batch(5)

    repository = DocumentRepository()
    documents = await repository.list_documents()

    assert len(documents) >= 5
```

### Uso em CLI dev

```python
# src/app/console/commands/seed_dev_data_command.py
async def seed_dev_data_command():
    """Popula dados fake para dev."""
    from database.factories.document_factory import DocumentFactory
    from src.support.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        DocumentFactory._meta.sqlalchemy_session = session
        await DocumentFactory.create_batch(50)
        await session.commit()
```

### Diferença prática Seed vs Factory

| Aspecto | Seed | Factory |
|---|---|---|
| Onde roda | Qualquer ambiente | Dev/Test apenas |
| Quantidade | Poucos registros essenciais | Muitos registros fake |
| Idempotência | Tracking via `seeds_executions` | Cada chamada cria novo |
| Dados | Reais (fonte "notion") | Fake (faker) |
| Acionamento | `python -m database.seeds` (deploy) | Pytest fixtures, CLI dev |
| Localização | `database/seeds/` | `database/factories/` |

## Ambientes

### Variáveis relevantes (`src/support/core/settings.py`)

```python
ENVIRONMENT: str = "development"   # development | staging | production
DEBUG: bool = True
ENABLE_SCHEDULER: bool = True

DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
DB_POOL_SIZE: int = 20
DB_MAX_OVERFLOW: int = 10
DB_POOL_TIMEOUT: int = 30
DB_POOL_RECYCLE: int = 3600
```

### Por ambiente

| Ambiente | Banco | Seeds | Factories | Scheduler |
|---|---|---|---|---|
| **Dev local** | Postgres via Docker | Todos (incluindo dev_*) | Sim | Normalmente on |
| **Teste** | Postgres dedicado | Mínimo | Sim | Off |
| **Staging** | Postgres gerenciado | Produção-safe apenas | Não | On em 1+ instância |
| **Produção** | Postgres gerenciado | Produção-safe apenas | Não | On em 1+ instância |

**Evite SQLite em testes.** Comportamento diverge do Postgres em detalhes que machucam (constraints, JSON, arrays). Use Postgres real via testcontainers ou container dedicado.

## Troubleshooting

**"Target database is not up to date" no autogenerate**
→ Aplique migrations pendentes primeiro: `alembic upgrade head`.

**Autogenerate vazio mesmo com mudanças no model**
→ O model não foi importado em `database/env.py`. Verifique imports e exports em `src/domain/{ctx}/models/__init__.py`.

**Autogenerate gerou drop + create para um rename**
→ Edite manualmente. Use `op.alter_column(..., new_column_name=...)`.

**Jobs rodam múltiplas vezes em múltiplas réplicas**
→ Não deveria. Verifique: (a) `apscheduler_jobs` existe no banco, (b) todas réplicas no mesmo Postgres, (c) `max_instances=1` em `src/support/core/scheduling/scheduler.py` preservado.

**Seed rodou duas vezes e duplicou dados**
→ Não era idempotente internamente E tracking falhou. Verifique: (a) `seeds_executions` existe, (b) seed na lista em `database/seeds/__init__.py`, (c) seed checa existência antes de inserir.

**"No active database session found in context"**
→ Código rodando fora de request sem popular o contexto. Em jobs/seeds, abra `AsyncSessionLocal()` e faça `CurrentAsyncSessionContext.set(session)` antes.

## Referências internas

- Convenções: `docs/conventions.md`
- Adicionando subdomínio (cria tabelas): `docs/adding-new-domain.md`
- Arquitetura geral: `docs/architecture.md`
- Testes (com factories): `docs/testing-guide.md`
- ADRs relevantes: `docs/adr/0005-*` (SQLAlchemy), `docs/adr/0006-*` (session)

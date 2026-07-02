# Oracle Borderless

Um **agente de IA no estilo "Claude Code" reposicionado como oráculo**: uma *single source of truth* consultável em linguagem natural. Qualquer pessoa faz uma pergunta em linguagem natural e recebe uma resposta útil, confiável e amigável, baseada **exclusivamente em fontes aprovadas**.

## O que é

- **Base de conhecimento no Notion via MCP** (Model Context Protocol) — o agente consome apenas documentos liberados.
- **Perguntas em linguagem natural** sobre regras de negócio do ecossistema e dados operacionais (ex.: resultados de alunos), com respostas em linguagem clara.
- **Nada confidencial** é ingerido ou exposto — o conteúdo vem só de fontes permitidas pelas restrições de acesso do MCP do Notion.
- Pensado para **produção**, com URL/domínio próprio e aparência de produto.

## Stack

- **Framework:** FastAPI (Python 3.13+)
- **ORM:** SQLAlchemy 2.0 (async `asyncpg` + sync `psycopg`)
- **Migrations:** Alembic
- **Validação:** Pydantic v2
- **Base de conhecimento:** Notion via MCP
- **Scheduler:** APScheduler (jobstore PostgreSQL)
- **Package manager:** UV

## Arquitetura

Padrão **Spatie Laravel Beyond CRUD adaptado ao FastAPI**, em três camadas:

- `src/app/` — pontos de entrada (HTTP, console/jobs)
- `src/domain/` — negócio, organizado por subdomínio (bounded contexts)
- `src/support/` — ferramental transversal (infra, integrações, utils)

Comece por **[`CLAUDE.md`](CLAUDE.md)** (regras e visão condensada) e **[`docs/architecture.md`](docs/architecture.md)** (arquitetura completa).

## Rodando em desenvolvimento

```bash
# Subir a aplicação
uvicorn main:app --reload

# Migrations
alembic upgrade head

# Seeds
python -m database.seeds

# Testes
pytest
```

## Pontos em aberto

Ainda a decidir em conjunto (não inventar): interface (chat web vs. contexto de código), arquitetura interna do agente, estratégia de ingestão/atualização da base de conhecimento e a **camada de autenticação** (haverá auth restrita ao ecossistema; mecanismo a definir).

## Documentação

- [`docs/architecture.md`](docs/architecture.md) — arquitetura completa
- [`docs/actions-vs-services.md`](docs/actions-vs-services.md) — Action vs Domain Service
- [`docs/conventions.md`](docs/conventions.md) — naming e estilo
- [`docs/adding-new-domain.md`](docs/adding-new-domain.md) — criar subdomínio novo
- [`docs/database-guide.md`](docs/database-guide.md) — migrations, seeds, factories
- [`docs/testing-guide.md`](docs/testing-guide.md) — testes
- [`docs/scaffolding-guide.md`](docs/scaffolding-guide.md) — comandos `make:*`

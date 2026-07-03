# Guia de Scaffolding (`make:*`)

Comandos CLI para gerar artefatos do projeto seguindo a arquitetura Spatie Beyond CRUD adotada (ver `CLAUDE.md` e `docs/architecture.md`). Inspiração: `php artisan make:*` do Laravel + `django-admin startapp`.

## Para agentes de IA

Quando o usuário pedir para criar **qualquer** artefato listado neste guia (subdomínio, Action, Controller, etc.), **prefira `python cli.py make:*`** em vez de criar arquivos manualmente. Os geradores:

- Aderem ao padrão canônico do projeto (mixins, type hints, imports corretos).
- Fazem auto-wiring de `__init__.py` e `database/env.py` (sem isso a migration quebra).
- Falham cedo se o arquivo já existe (a menos que `--force`), evitando sobrescrita acidental.

Após gerar, faça os ajustes específicos do caso de uso (campos, lógica). **Não regenere um arquivo já editado** sem `--force`, e quando usar `--force`, peça confirmação ao usuário.

## Quando usar cada comando

| Preciso criar... | Use |
|---|---|
| Subdomínio novo do zero | `make:domain {nome}` |
| Action nova em subdomínio existente | `make:action {ctx} {VerboSubstantivo}` |
| Endpoint REST novo | `make:request` + `make:response` + `make:controller` (+ editar `routes/{ctx}.py`) |
| Job agendado | `make:job {nome}` (+ registrar em `schedule.py`) |
| CLI command novo | `make:command {nome}` |
| Seed de dados base | `make:seed {nome}` (+ wiring manual em `seeds/__init__.py`) |
| Factory para testes | `make:factory {ctx} {Entity}` |
| Apenas Entity / Model / Repository / Mapper / DTO | `make:entity` / `make:model` / `make:repository` / `make:mapper` / `make:dto` |

Se o que você quer não está aqui, **não exista um gerador para isso** — siga `docs/adding-new-domain.md` ou `docs/conventions.md`.

## Inventário completo

Todos os comandos suportam `--force` para sobrescrever arquivos existentes. O default é falhar cedo com mensagem amigável.

| Comando | Argumentos | Cria | Auto-wires |
|---|---|---|---|
| `make:domain` | `{name}` | Subdomínio completo com CRUD | `database/env.py` + `__init__.py` de cada subpasta |
| `make:entity` | `{ctx} {name}` | `src/domain/{ctx}/entities/{name}.py` | `entities/__init__.py` |
| `make:model` | `{ctx} {name}` | `src/domain/{ctx}/models/{name}.py` | `models/__init__.py` + `database/env.py` |
| `make:repository` | `{ctx} {name}` | `src/domain/{ctx}/repositories/{name}_repository.py` | `repositories/__init__.py` |
| `make:mapper` | `{ctx} {name}` | `src/domain/{ctx}/mappers/{name}_mapper.py` | `mappers/__init__.py` |
| `make:action` | `{ctx} {VerbNoun} [--entity NAME]` | `src/domain/{ctx}/actions/{verb_noun}_action.py` | `actions/__init__.py` |
| `make:dto` | `{ctx} {name}` | `src/domain/{ctx}/dtos/{name}.py` | `dtos/__init__.py` |
| `make:controller` | `{ctx} {name}` | `src/app/api/controllers/{name}_controller.py` | — |
| `make:request` | `{name}` | `src/app/api/requests/{name}_request.py` | — |
| `make:response` | `{ctx} {name}` | `src/app/api/responses/{name}_response.py` | — |
| `make:route` | `{ctx} [--public]` | `src/app/api/routes/{ctx}.py` | autodiscovery |
| `make:job` | `{name}` | `src/app/console/jobs/{name}_job.py` | — |
| `make:command` | `{name} [--signature ...]` | `src/app/console/commands/{name}_command.py` | autodiscovery |
| `make:seed` | `{name}` | `database/seeds/{name}_seed.py` | imprime instrução para wiring manual |
| `make:factory` | `{ctx} {name}` | `database/factories/{name}_factory.py` | — |

## Receitas

### Subdomínio novo do zero

Cria estrutura completa (Entity, Model, Mapper, Repository, DTO, 5 Actions CRUD, Controller, Request, Response, Route) com auto-wiring.

```bash
python cli.py make:domain conversation
```

Em ~1 segundo gera os arquivos em `src/domain/conversations/` + `src/app/api/`. Cobre ~90% de `docs/adding-new-domain.md`.

**Próximos passos** (impressos pelo comando):

1. Ajuste campos em `src/domain/conversations/{entities,models,dtos}/conversation.py`.
2. `alembic revision --autogenerate -m "create conversations table"` — o auto-wiring de `database/env.py` garante que o autogenerate enxergue o Model novo.
3. `alembic upgrade head`.
4. (Opcional) `make:factory conversations Conversation` para tests/dev.
5. Acesse via `/conversations`.

### Pattern de listagem (filter / sort / paginação opcional)

Todo subdomínio gerado por `make:domain` produz uma listagem rica que segue o padrão único do projeto:

- **Repository:** `get_{plural}(relations, filter, sort, page, per_page)` retorna `Paginator | list[Entity]` — pagina apenas se `page` for informado.
- **Action:** `List{Plural}Action.execute(list_dto)` recebe um `{Entity}List` e delega ao repository, montando `RelationshipFilter` e `RelationshipSort`.
- **Controller:** `list_{plural}(filters: QueryFilterRequest = Depends(get_query_filters))` constrói o `{Entity}List`, deixa um comentário para você setar `relationships`, e mapeia o resultado via `from_paginator` ou `from_list`.
- **DTO:** `{Entity}List` extends `QueryFilterRequest` (com `relationships: list[str]` herdado) — adicione campos de filtro custom se quiser.
- **Response:** ganha `from_list(items)` e `from_paginator(paginator)` automaticamente.

**Como o cliente HTTP usa:**

| Query string | Resultado |
|---|---|
| `GET /documents` | lista plana de Entities (sem paginação) |
| `GET /documents?page=2&per_page=20` | `{ items, total, page, per_page, pages }` paginado |
| `GET /documents?filter[status]=approved&filter_like[title]=onboarding` | filtrado por igualdade + LIKE |
| `GET /documents?filter[source.key]=notion` | filter cruza relationship via dot notation |
| `GET /documents?sort[created_at]=desc&sort[source.name]=asc` | ordenação inclusive por relationship |

**Personalizar relationships permitidos:** abra o controller gerado e descomente a linha de exemplo:

```python
async def list_documents(filters: QueryFilterRequest = Depends(get_query_filters)):
    list_dto = DocumentList(**filters.model_dump())
    list_dto.relationships = ["source"]  # whitelist
    ...
```

Fica permitido o cliente passar `?relationships=...` (já vem em `QueryFilterRequest`), mas o ponto canônico de configuração é o controller — assim você controla o que pode ser eager-loaded.

**Por que pagina só com `?page`:** evita quebrar consumidores que esperam lista plana (ex: um select de UI). Se quiser sempre paginar, altere o controller para forçar `list_dto.page = list_dto.page or 1`.

### Adicionar Action em subdomínio existente

```bash
python cli.py make:action documents ArchiveDocument
# → src/domain/documents/actions/archive_document_action.py
# → documents/actions/__init__.py exporta ArchiveDocumentAction
```

A Action gerada fica como stub:

```python
class ArchiveDocumentAction:
    def __init__(self):
        self.repository = DocumentRepository()

    async def execute(self):
        raise NotImplementedError("Implement ArchiveDocumentAction.execute")
```

Edite a assinatura de `execute()` e a lógica. O Repository já é instanciado.

Se a Action manipula uma Entity diferente da inferida pelo nome do contexto, passe `--entity`:

```bash
python cli.py make:action documents ReindexAll --entity document
```

### Adicionar endpoint REST a subdomínio existente

```bash
python cli.py make:request UpdateDocumentStatus
python cli.py make:response documents DocumentSummary
python cli.py make:controller documents DocumentSummary  # se for controller dedicado
```

Em seguida, abra `src/app/api/routes/documents.py` e adicione:

```python
router.post("/{document_id}/status")(DocumentController.update_status)
```

### Job agendado

```bash
python cli.py make:job SyncKnowledgeBase
# → src/app/console/jobs/sync_knowledge_base_job.py
```

Implemente `async def action()` e registre em `src/app/console/schedule.py`:

```python
schedule.call(SyncKnowledgeBaseJob).hourly()
```

### Seed novo

```bash
python cli.py make:seed DocumentSources
# → database/seeds/document_sources_seed.py
```

O comando **não atualiza `database/seeds/__init__.py`** automaticamente (a lista está dentro do corpo de `run_all_seeders()` — AST-edit é arriscado). Adicione manualmente:

```python
# database/seeds/__init__.py
from .document_sources_seed import DocumentSourcesSeed
# ...
seeders = [
    DocumentSourcesSeed,    # ← adicione aqui
]
```

### CLI command novo

```bash
python cli.py make:command DocumentsIngest --signature "documents:ingest {page_id:str} {--force:bool}"
# → src/app/console/commands/documents_ingest_command.py
```

A signature é a DSL Laravel-like documentada no `CLAUDE.md` (seção Commands). Se omitir `--signature`, o comando deriva de `documents ingest` → `documents:ingest`.

## Comandos de infraestrutura

Além dos `make:*` (que geram código), o `cli.py` expõe comandos administrativos para tarefas operacionais comuns. São auto-descobertos pelo mesmo loader e seguem o mesmo Command pattern.

| Comando | Faz | Equivalente direto |
|---|---|---|
| `db:migrate` | Aplica migrations Alembic até o head | `alembic upgrade head` |
| `db:seed` | Roda seeds pendentes (rastreadas em `seeds_executions`) | `python -m database.seeds` |

Exemplos:

```bash
python cli.py db:migrate
python cli.py db:seed
```

## Convenções de naming

Os geradores aceitam input em qualquer caixa (`"ingest document"`, `"ingest_document"`, `"IngestDocument"`) e produzem nomes canônicos automaticamente:

| Input | Arquivo | Classe |
|---|---|---|
| `ingest document` | `ingest_document_action.py` | `IngestDocumentAction` |
| `IngestDocument` | `ingest_document_action.py` | `IngestDocumentAction` |
| `Document` (entity) | `document.py` | `Document` |
| `documents` (domain via `make:domain`) | `document.py` (singular) | `Document` + tabela `documents` |

Pluralização é simples (boa o suficiente para nomes técnicos): `document → documents`, `entry → entries`, `box → boxes`, `status → status` (latinismo).

Se a pluralização inferida não couber para seu domínio (`Person → Persons` em vez de `People`), prefira o atômico (`make:entity person` + `make:model person`...) e ajuste manualmente o nome do contexto.

## Limitações conhecidas

- **Sem inline schema.** Os Models são gerados só com mixins (`HasUUID`, `HasTimestamps`); você adiciona campos manualmente. O suporte a `--fields name:str:255,title:str:unique` está **fora** do MVP.
- **Sem auto-wiring de seeds.** A lista `seeders` em `database/seeds/__init__.py` precisa ser editada à mão (limitação intencional para evitar AST-edit arriscado).
- **Sem geração de testes.** Boilerplate de teste é pequeno e contextual; segue o padrão do projeto.
- **Sem `make:enum`, `make:service`.** O primeiro é trivial (1 classe Enum); o segundo é raro pelo design (a arquitetura desencoraja Domain Services — ver `docs/actions-vs-services.md`).
- **Pluralização inglesa só.** Para nomes em PT-BR, prefira o atômico ou ajuste manualmente.

## Como funciona internamente

- **Templates Jinja2:** em `src/support/core/console/scaffolding/templates/`. Espelham os exemplos canônicos de `docs/adding-new-domain.md`.
- **Engine:**
  - `Naming` — conversões de caixa (snake/Pascal) e pluralização.
  - `Generator` — render Jinja2 + grava arquivo + checa overwrite.
  - `Wiring` — append idempotente em `__init__.py` (`__all__` editado preservando sintaxe) e injeção em `database/env.py`.
  - `Scaffolder` — orquestra o pipeline (render → write → wire → echo) com tradução de `FileExistsError` → `typer.Exit(1)`.
- **Comandos:** cada `MakeXCommand` em `src/app/console/commands/` é uma subclasse de `Command` (auto-discovered pelo `cli.py`). Acessam input via `self.input["..."]`, chamam `Scaffolder.create(...)`.

Para adicionar um novo gerador, use os `make:*` existentes como exemplo e o Command pattern descrito no `CLAUDE.md`.

## Convenção do projeto

Os geradores **respeitam** as regras inegociáveis listadas em `CLAUDE.md`:

- Entities são dataclasses puras (sem SQLAlchemy).
- Models usam mixins padrão (`HasUUID, HasTimestamps, ApplyRelations`).
- Repositories acessam sessão via `CurrentAsyncSessionContext.get()`.
- Actions trabalham com Entities, lançam exceções de domínio.
- Controllers são finos (`@staticmethod`, sem regra).
- Jobs são wrappers — a lógica vive na Action.

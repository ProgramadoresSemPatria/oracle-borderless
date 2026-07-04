# Milestone 1 — Oráculo: fatia vertical (RAG Notion + web search → resposta com citação, streaming)

**Data:** 2026-07-04
**Status:** Design aprovado — pronto para plano de implementação
**Escopo:** Primeiro milestone da arquitetura de agente (ver "Roadmap" no fim). Entrega o caminho ponta-a-ponta mais curto: pergunta → RAG na base (Notion) + web search → resposta fundamentada e citada, em streaming, com UI web mínima.

---

## 1. Contexto e objetivo

Construir a **fatia vertical fina** do Oracle Borderless: o menor caminho que já entrega um oráculo funcional. Fora de escopo neste milestone (viram milestones próprios): memória em camadas (episódica/semântica/procedural), summarizer, e LLMOps (trace/eval/gate/release).

Decisões do usuário que ancoram este design:
- **Sequência:** fatia vertical fina primeiro (MVP), camadas por cima depois.
- **Interface:** API (SSE) **+ UI web mínima** de chat. *Isto resolve, na prática, o ponto-em-aberto "chat web vs. contexto de código" do CLAUDE.md em favor de chat web.* A UI é deliberadamente mínima (HTML+JS puro, sem framework, sem build step) para não comprometer o projeto com um frontend pesado.
- **Estado:** stateless — o histórico vem no corpo do request; nada é persistido ainda (persistência é o Milestone 2).
- **Fonte RAG:** caminho real Notion MCP + seed/fake de markdown para dev e teste (desbloqueia o RAG sem depender da auth do Notion).
- **Auth:** Cloudflare Access (edge). Ver seção 9.
- **Web search:** incluído no M1 como tool secundária (Tavily).

O que **já existe** no repositório e será reutilizado:
- `src/support/agent/ports.py` — `OracleEnginePort`, `AgentMessage`, `AgentStreamChunk` (ADR-0007).
- `src/support/agent/prompts.py` — `SYSTEM_PROMPT` (grounding, citação, recusa, anti-injection).
- Clients: `llm/` (Claude/GPT selecionável), `notion/`, `tavily/`, `embeddings/`.
- `src/domain/documents/services/chunking_service.py` — `ChunkingService`.
- `src/domain/shared/value_objects/citation.py` — `Citation`.
- Fakes de teste: `fake_oracle_engine`, `fake_embeddings_client`, `fake_tavily_client`.
- Settings prontas: `DB_*`, `RAG_TOP_K/CHUNK_SIZE/CHUNK_OVERLAP`, `EMBEDDING_*`, `LLM_PROVIDER`, `NOTION_MCP_*`, `TAVILY_API_KEY`.
- Deps prontas no `pyproject.toml`: `pgvector`, `pydantic-ai`, `anthropic`, `openai`, `tavily-python`, `asyncpg`, `psycopg`, `alembic`.

---

## 2. Infra — Postgres + pgvector (banco novo)

O usuário ainda não tem banco. Passos:

1. **Trocar a imagem** em `docker/docker-compose.yml`: de `postgres:16-alpine` para **`pgvector/pgvector:pg16`** (imagem oficial com a extensão `vector` embutida). Mantém `container_name`, user/senha (`oracle`/`oracle`), db (`oracle_borderless`), porta `5432` e o volume `oracle_borderless_pgdata`.
2. Subir: `docker compose -f docker/docker-compose.yml up -d`.
3. Criar o banco de testes (a suíte de integração usa `oracle_borderless_test`):
   `docker exec oracle_borderless_db createdb -U oracle oracle_borderless_test`
4. **Primeira migration** (Alembic) roda `CREATE EXTENSION IF NOT EXISTS vector;` **antes** de criar as tabelas, e cria `documents` e `document_chunks`.
5. `alembic upgrade head`.

Nota de teste: a mesma extensão precisa existir no banco de teste. Como usam a mesma instância Postgres (mesma imagem pgvector), a migration `CREATE EXTENSION` cobre ambos quando aplicada em cada banco.

---

## 3. Subdomínio `documents/` — persistência + busca vetorial

Segue Entity ≠ Model + Mapper + Repository (ADR-0003).

### Entities (dataclass puras — sem SQLAlchemy)
- `Document`: `uuid`, `notion_page_id`, `title`, `content`, `source_url`, `status` (`"approved"|"pending"|"archived"`), `created_at`, `updated_at`, `deleted_at`. Método `is_approved()`.
- `DocumentChunk`: `uuid`, `document_id`, `ordinal` (int, ordem no doc), `content`, `embedding: list[float] | None`.

### Models (SQLAlchemy)
- `DocumentModel` (`documents`): conforme exemplo do CLAUDE.md (`notion_page_id` unique+index, `status` index).
- `DocumentChunkModel` (`document_chunks`): `document_id` (FK → documents), `ordinal`, `content` (Text), `embedding` = coluna `Vector(settings.EMBEDDING_DIM)` via `pgvector.sqlalchemy.Vector`. Índice **HNSW com `vector_cosine_ops`** para busca por similaridade (melhor recall/latência de leitura; custo maior de escrita/memória é aceitável no volume inicial de um oráculo interno). Criado na migration junto da tabela.

### Mappers
- `DocumentMapper` e `DocumentChunkMapper` (`to_entity` / `to_model_attrs`).

### Repositories (fronteira em Entities, delegam ao Mapper)
- `DocumentRepository`: `get_by_notion_page_id`, `upsert(document) -> Document`, `get_by_id`.
- `DocumentChunkRepository`:
  - `replace_for_document(document_id, chunks: list[DocumentChunk])` — apaga chunks antigos e insere os novos (suporta re-ingestão idempotente).
  - `search_similar(embedding: list[float], top_k: int) -> list[DocumentChunk]` — usa operador de distância cosseno do pgvector, ordenado ascendente, `LIMIT top_k`. `top_k` default = `settings.RAG_TOP_K`.

Sessão sempre via `CurrentAsyncSessionContext.get()` (ADR-0006).

---

## 4. Ingestão (source-agnostic, DRY)

Um pipeline único, independente da fonte:

- `IngestDocumentAction.execute(document: Document) -> Document`
  1. `ChunkingService.chunk(document.content)` → lista de trechos (usa `RAG_CHUNK_SIZE`/`RAG_CHUNK_OVERLAP`).
  2. `EmbeddingsClient.embed([...])` → vetores (batch).
  3. `DocumentRepository.upsert(document)` + `DocumentChunkRepository.replace_for_document(...)`.
  - **Idempotente** (regra 8): re-ingerir a mesma `notion_page_id` substitui doc+chunks, não duplica.

Fontes que alimentam a Action:
- **Real (Notion MCP):** `NotionClient.get_page(page_id) -> Document` (valida `is_approved()` antes de ingerir — regra 4: nada não-aprovado entra). Command `knowledge:ingest {page_id}` em `src/app/console/commands/`.
- **Dev/teste (seed):** lê markdown de `database/seeds/knowledge/*.md` → monta `Document` (status `"approved"`, `source_url` = caminho/URL fictícia) → mesma `IngestDocumentAction`. Registrada em `database/seeds/__init__.py` com tracking (regra 9). Fake de `NotionClient` para os testes unitários.

---

## 5. Tools do agente

Cada tool devolve conteúdo de fonte **entre marcadores `<<TOOL_CONTENT>>…<</TOOL_CONTENT>>`** (dado não-confiável, conforme o system prompt) e metadados de fonte para citação:

- `search_knowledge_base(query: str)`: embed da query → `DocumentChunkRepository.search_similar` → retorna trechos + `title`/`source_url` de cada `Document` de origem.
- `web_search(query: str)`: `TavilyClient.search` → título + snippet + URL de cada resultado.
- `fetch_notion_page(page_id: str)`: `NotionClient.get_page` — conteúdo completo/atualizado quando a busca por chunk não basta.

As tools são registradas no engine (seção 6), não no domínio.

---

## 6. `OracleEngine` real (Pydantic AI) — implementa `OracleEnginePort`

- Arquivo: `src/support/agent/oracle_engine.py`.
- Monta um `pydantic_ai.Agent` com: `SYSTEM_PROMPT`, as 3 tools da seção 5, e o modelo resolvido das settings (`LLM_PROVIDER` → Claude ou GPT).
- `stream_answer(question, history: list[AgentMessage]) -> AsyncIterator[AgentStreamChunk]`:
  - emite chunks `type="text"` com os deltas de texto conforme o modelo gera;
  - ao final, emite um chunk `type="sources"` com as `Citation` coletadas das tool calls executadas.
- **Fronteira (ADR-0007):** o domínio nunca importa `pydantic_ai`. Só o engine importa. Factory `get_oracle_engine() -> OracleEnginePort` na fronteira (`src/support/agent/`), usada pelo controller/composição.
- Guardrail de fim-de-loop (mínimo M1): garantir resposta final não-vazia; se nenhuma fonte sustentou a resposta, o prompt já instrui recusa honesta.

---

## 7. Caso de uso + API + UI

### Domínio
- `AnswerQuestionAction(engine: OracleEnginePort)` em `src/domain/conversations/actions/answer_question_action.py`.
- `execute(question: str, history: list[AgentMessage]) -> AsyncIterator[AgentStreamChunk]` — fino, delega ao engine (regra 5: controller fino, composição na Action).

### API
- Request: `AskQuestionRequest { question: str, history: list[{role, content}] }` em `src/app/api/requests/`.
- `ConversationController.ask(request, data)` em `src/app/api/controllers/` → resolve engine via factory, instancia `AnswerQuestionAction`, retorna `StreamingResponse` (media type `text/event-stream`) mapeando cada `AgentStreamChunk` para um evento SSE (texto e, no fim, evento `sources` com as citações serializadas).
- Rota: `src/app/api/routes/conversations.py` com `public_router` (autodiscovery). `POST /conversations/ask`. Sem auth de app (protegido por Cloudflare Access na borda — seção 9).

### UI web mínima
- `src/app/web/` — uma página estática/SSR (`index.html` + JS puro) servida por rota dedicada ou `StaticFiles`. Campo de pergunta, área de resposta que renderiza o stream SSE token-a-token, e lista de citações ao final. Sem framework, sem bundler.

---

## 8. Guardrails (mínimos no M1)

- Grounding + citação obrigatória + recusa honesta + anti-injection: **já no `SYSTEM_PROMPT`**.
- Todo conteúdo de tool é envolvido em `<<TOOL_CONTENT>>…<</TOOL_CONTENT>>` e tratado como dado, nunca comando.
- Regra 4 (nada confidencial): ingestão só aceita documentos `is_approved()`; respostas só citam fontes ingeridas/aprovadas ou web search explícito.

---

## 9. Autenticação — Cloudflare Access (edge)

- **Modelo:** Cloudflare Access fica **na frente** da aplicação. O usuário autentica no CF antes de a requisição chegar ao FastAPI; o CF injeta os headers `Cf-Access-Jwt-Assertion` e `Cf-Access-Authenticated-User-Email`.
- **No M1:** a app **não** implementa validação de auth (alinhado ao CLAUDE.md: não implementar auth concreta na app enquanto o mecanismo não estiver fechado). O endpoint segue público no nível da app; a proteção é de infraestrutura (CF Access).
- **Placeholder para depois (fora do M1):** uma dependency do FastAPI que valida o JWT `Cf-Access-Jwt-Assertion` contra as chaves públicas do CF e extrai o e-mail do usuário. Registrada como trabalho futuro, não implementada agora.
- **Config do túnel/aplicação Cloudflare Access:** feita no painel Cloudflare pelo usuário (fora do código). Documentar no README de deploy quando o M1 for pra produção.

---

## 10. Configuração de ambiente (`.env`) — preencher no final

Placeholders que o usuário preenche ao final (deixar em branco no `.env.example`/`.env`):

```
# LLM
ANTHROPIC_API_KEY=          # preencher
# ou OPENAI_API_KEY=        # se LLM_PROVIDER=openai

# Embeddings (OpenAI)
OPENAI_API_KEY=             # necessário para embeddings mesmo usando Claude no chat

# Notion MCP — usuário JÁ possui o access token; preencher no final
NOTION_MCP_URL=             # preencher
NOTION_MCP_TOKEN=           # preencher (access token do Notion que o usuário já tem)

# Web search
TAVILY_API_KEY=             # preencher

# DB — defaults do docker-compose já servem em dev (oracle/oracle)
```

> Nota: `EMBEDDING_PROVIDER` está fixado em `openai` (ADR-0008), então `OPENAI_API_KEY` é necessário para embeddings mesmo com `LLM_PROVIDER=anthropic`.

---

## 11. Testes

- **Unit:**
  - roundtrip `DocumentMapper`/`DocumentChunkMapper` (entity ↔ model attrs);
  - `IngestDocumentAction` com fakes (chunking real + `fake_embeddings_client` + repos fake/stubs);
  - wrapping das tools (marcadores `<<TOOL_CONTENT>>`, metadados de citação);
  - `OracleEngine` com LLM fake (deltas + chunk `sources`);
  - `AnswerQuestionAction` com `fake_oracle_engine` (já existe);
  - fake de `NotionClient` (novo).
- **Integração (banco de teste com pgvector):**
  - ingest → `search_similar` retorna os chunks esperados por similaridade;
  - endpoint `POST /conversations/ask` responde em streaming (engine fake ou LLM stubado).

---

## 12. Custo & Qualidade

- **Barato por design:** embeddings `text-embedding-3-small`; `web_search` só quando a base interna não cobre (instruído no prompt); `top_k=6`.
- **Alavanca de custo registrada:** `ANTHROPIC_MODEL` está em `claude-opus-4-8` (caro). Para o oráculo em produção, considerar um modelo menor. Ajustável via settings — **não alterado neste milestone**, apenas registrado.
- **Alavancas de qualidade do M1:** `RAG_CHUNK_SIZE`/`RAG_CHUNK_OVERLAP`, `RAG_TOP_K`, e o prompt de grounding. Ficam mensuráveis de verdade só no Milestone 4 (LLMOps/eval).

---

## Roadmap (contexto — milestones seguintes)

1. **M1 (este):** fatia vertical — RAG(Notion+web) → resposta citada, streaming, UI mínima.
2. **M2 — Memória episódica:** subdomínio `conversations/` (Conversation/Message em SQL), persistir turnos, carregar recência na working memory.
3. **M3 — Memória semântica + Summarizer:** `SummarizeConversationJob` (modelo barato, após N chats, idempotente) que destila fatos; memória semântica (fatos/perfil em vetor) recuperada junto ao RAG.
4. **M4 — LLMOps:** trace por run (Langfuse/OTel) → observe → eval (LLM-as-judge) → gate → release de prompt/modelo/tool/top-k.

Transversal: memória procedural (system prompt + tools) evolui ao longo de M1–M3.

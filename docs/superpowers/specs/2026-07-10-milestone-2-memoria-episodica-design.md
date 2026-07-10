# Milestone 2 — Memória episódica (persistir turnos + retomar conversas)

**Data:** 2026-07-10
**Status:** Design aprovado — pronto para plano de implementação
**Escopo:** Segundo milestone do roadmap de agente (ver M1). Dá memória de conversa ao oráculo: o servidor passa a ser fonte da verdade dos turnos, carrega recência por orçamento de tokens na working memory, e o usuário pode listar e reabrir conversas antigas.

---

## 1. Contexto e objetivo

O M1 entregou a fatia vertical **stateless**: o cliente mandava o histórico inteiro no corpo do request e nada era persistido. O M2 troca isso por **memória episódica**: turnos gravados em SQL, servidor como fonte da verdade, recência carregada a cada pergunta.

Decisões do usuário que ancoram este design (do brainstorming):

- **Contrato:** server-side com `conversation_id`. O servidor gera o id no 1º turno e o devolve; nos turnos seguintes o cliente manda só `{conversation_id, question}` e o servidor carrega a recência do banco. Fonte da verdade única no servidor.
- **Dono da conversa:** `user_email` lido do header `Cf-Access-Authenticated-User-Email` (injetado pelo Cloudflare Access na borda), **best-effort e não validado** — a validação do JWT do CF fica para o milestone de auth. `user_email` é nullable (null em dev/local sem o header). Grava o dono agora para não exigir retrabalho de schema quando a auth fechar.
- **Recência:** orçamento de tokens (não "últimos N turnos"). Mais robusto contra mensagens gigantes.
- **Escopo:** encanamento de memória **+ retomar conversas** — inclui endpoints de listar/abrir e UI mínima de sidebar.
- **Mensagem:** persiste `content` **+ `sources` (JSONB)**, para a conversa reaberta reaparecer com as citações e para o M3 poder minerar histórico.

O que **já existe** no M1 e será reutilizado/ajustado:
- `src/support/agent/ports.py` — `AgentMessage`, `AgentStreamChunk`, `KnowledgeSnippet`.
- `src/support/agent/oracle_engine.py` — `OracleEngine.stream_answer(question, history, knowledge)`.
- `src/domain/documents/actions/search_knowledge_base_action.py` — retrieval, reusado no fluxo.
- `src/domain/conversations/actions/answer_question_action.py` — **modificado** neste milestone.
- `src/app/api/controllers/conversation_controller.py`, `routes/conversations.py`, `requests/ask_question_request.py`, `src/app/web/index.html` — **modificados**.
- Infra transversal: `DBSessionMiddleware`, `BackgroundTaskMiddleware`, `BackgroundTaskContext`, `CurrentAsyncSessionContext`, `CurrentRequestContext`, `AsyncSessionLocal`.

O subdomínio `src/domain/conversations/` já tem o esqueleto de pastas (`entities/`, `models/`, `mappers/`, `repositories/`, `actions/`, `dtos/`, `enums/`, `services/`) — hoje vazias exceto a Action de M1.

---

## 2. Data model — subdomínio `conversations/`

Segue Entity ≠ Model + Mapper + Repository (ADR-0003).

### Entities (dataclass puras — sem SQLAlchemy)
- `Conversation`: `uuid`, `user_email: str | None`, `title: str | None`, `created_at`, `updated_at`, `deleted_at`.
  - `title` derivado da 1ª pergunta do usuário (truncado ~80 chars) — só para rotular a sidebar.
- `Message`: `uuid`, `conversation_id: UUID`, `role: str` (`"user" | "assistant"`), `content: str`, `sources: list[Citation] | None` (só no assistant), `created_at`.
  - Ordenação por `created_at`. A PK é UUID v7 (monotônico), que serve de desempate estável — **sem** coluna `ordinal` explícita.

### Models (SQLAlchemy)
- `ConversationModel` (`conversations`): `user_email` = `String(320)` nullable + index; `title` = `String(120)` nullable. Usa mixins `HasUUID`, `HasTimestamps` (que já trazem `deleted_at`), `ApplyRelations`.
- `MessageModel` (`messages`): `conversation_id` = FK → `conversations.uuid` (index); `role` = `String(16)`; `content` = `Text`; `sources` = `JSONB` nullable (`sqlalchemy.dialects.postgresql.JSONB`); herda `created_at` do mixin de timestamps. Índice composto `(conversation_id, created_at)` para carregar recência com eficiência.

### Mappers
- `ConversationMapper` e `MessageMapper` (`to_entity` / `to_model_attrs`).
  - `MessageMapper` serializa/desserializa `sources` entre `list[Citation]` (entity) e lista de dicts (JSONB). A conversão Citation ↔ dict fica no mapper (fronteira), não vaza para o repository.

### Migration
- `database/migrations/versions/0002_conversations.py` (revisão após `0001_documents_pgvector`): cria `conversations` e `messages` com o índice composto. Não precisa de extensão nova (JSONB é nativo do Postgres).

Sessão sempre via `CurrentAsyncSessionContext.get()` (ADR-0006).

---

## 3. Recência por orçamento de tokens

- Novas settings em `src/support/core/settings.py`:
  - `MEMORY_RECENCY_TOKEN_BUDGET: int = 2000` — teto de tokens de histórico injetado na working memory.
  - `MEMORY_RECENCY_MAX_MESSAGES: int = 50` — cap defensivo de linhas lidas do banco.
- **Contagem de tokens:** heurística barata `max(1, len(texto) // 4)` — **não** adiciona dependência nova (regra 10). Precisão real (ex. tiktoken) só passa a importar no M4 (eval); registrada como alavanca futura, não implementada agora.
- `MessageRepository.load_recent(conversation_id) -> list[AgentMessage]`:
  1. `SELECT ... WHERE conversation_id = :id ORDER BY created_at DESC LIMIT MEMORY_RECENCY_MAX_MESSAGES`.
  2. Acumula do mais novo ao mais antigo, somando tokens estimados, até estourar `MEMORY_RECENCY_TOKEN_BUDGET`.
  3. Reverte para ordem cronológica e converte para `list[AgentMessage]` (só `role`/`content`; `sources` não vai para o prompt).

---

## 4. Repositories & Actions

### Repositories (fronteira em Entities, delegam ao Mapper)
- `ConversationRepository`: `get_by_id(uuid)`, `get_or_create(conversation_id: UUID | None, user_email: str | None) -> Conversation`, `list_by_user(user_email: str | None) -> list[Conversation]`.
- `MessageRepository`: `append(message: Message) -> Message`, `load_recent(conversation_id) -> list[AgentMessage]`, `list_by_conversation(conversation_id) -> list[Message]`.

### Actions
- **`AnswerQuestionAction` (modificar).** Assinatura nova: `execute(question, conversation_id: UUID | None, user_email: str | None) -> tuple[UUID, AsyncIterator[AgentStreamChunk]]`. Fluxo no escopo do request (sessão viva):
  1. `ConversationRepository.get_or_create(conversation_id, user_email)` — regra de ownership/404 na seção 5.
  2. Se a conversa é nova e sem título, define `title` a partir da 1ª pergunta (truncada).
  3. `MessageRepository.append(user message)`.
  4. `MessageRepository.load_recent(...)` → `history`.
  5. `SearchKnowledgeBaseAction.execute(question)` → `knowledge` (retrieval, como no M1).
  6. Retorna `(conversation.uuid, engine.stream_answer(question, history, knowledge))`.
  - Compõe outras Actions/repos (regra 6), controller fica fino (regra 5).
- **`AppendAssistantMessageAction`** (persistência pós-stream): `execute(conversation_id, content, sources)` — grava a resposta do oráculo. Chamada de dentro da background task (seção 5), que provê a sessão.
- **`ListConversationsAction`**: `execute(user_email) -> list[Conversation]`.
- **`GetConversationAction`**: `execute(conversation_id) -> tuple[Conversation, list[Message]]`.

---

## 5. Persistência pós-stream (ponto crítico)

Durante o streaming SSE **não há sessão de banco**: o `DBSessionMiddleware` (BaseHTTPMiddleware) commita e limpa o `CurrentAsyncSessionContext` assim que o handler retorna — antes de o corpo SSE ser transmitido. É por isso que o M1 faz o retrieval *antes* de retornar o `StreamingResponse`. O M2 mantém esse princípio:

- **Conversa + user message:** gravadas *up-front*, no escopo do request (sessão viva), dentro do `AnswerQuestionAction`, antes de retornar o stream.
- **Assistant message:** o texto e as citações são acumulados no gerador SSE conforme os chunks chegam. Ao final do stream **com sucesso**, o controller agenda uma **background task** (via `BackgroundTaskContext` / `response.background`, que o Starlette executa após o corpo ser enviado). O wrapper da task:
  1. Abre `AsyncSessionLocal()` e seta `CurrentAsyncSessionContext` — exatamente o padrão de `Job.execute()`, dos Commands e dos Seeds.
  2. Chama `AppendAssistantMessageAction`.
  3. Commita e limpa o contexto.
- **Falha no meio do stream:** **não** persistir o assistant parcial (histórico limpo). A user message já está gravada; a pessoa repergunta. O gerador emite o evento SSE `error` (comportamento herdado do M1) e não agenda a task de assistant.

**Risco a validar na implementação:** confirmar que `response.background` executa mesmo com `StreamingResponse` sob `BaseHTTPMiddleware` (há históricos de incompatibilidade dependendo da versão do Starlette). Se não executar de forma confiável, o fallback é persistir num `asyncio` task disparado dentro do próprio gerador (abrindo sua própria sessão), ainda seguindo o padrão de sessão-própria. A decisão entre os dois é validada com um teste de integração que lê o banco após o stream.

### Ownership e existência (best-effort)
- `conversation_id = None` → cria conversa nova (id gerado pelo servidor).
- `conversation_id` informado mas **inexistente** → 404 (não recria com id do cliente; previsível).
- `conversation_id` existe, mas `conversation.user_email` e o `user_email` do header são **ambos não-nulos e diferentes** → 403.
- Qualquer um dos dois nulo (ex. dev sem header CF) → permite (best-effort, sem auth real ainda).

---

## 6. API & UI

### API
- **`AskQuestionRequest` muda (breaking vs. M1):** `{ question: str, conversation_id: UUID | None = None }` — remove `history`. O servidor carrega a recência.
- **`ConversationController.ask`:** lê `user_email` do header `Cf-Access-Authenticated-User-Email` (best-effort); chama `AnswerQuestionAction` (retrieval + persist da user message no escopo do request); retorna `StreamingResponse`. O gerador SSE emite, nesta ordem:
  1. evento `conversation` com `{ "id": <conversation_id> }` — o cliente guarda para os próximos turnos;
  2. eventos `token` (deltas de texto);
  3. evento `sources` (citações);
  4. evento `done`.
  Ao concluir com sucesso, agenda a background task de persistência do assistant (seção 5). Em falha, emite `error` (como no M1) e não agenda.
- **`ConversationController.list`:** `GET /conversations` → `ListConversationsAction(user_email)` → lista de `ConversationSummaryResponse { id, title, updated_at }`.
- **`ConversationController.get`:** `GET /conversations/{conversation_id}` → `GetConversationAction` → `ConversationDetailResponse { id, title, messages: [MessageResponse { role, content, sources }] }`.
- **Rotas** em `src/app/api/routes/conversations.py` (`public_router`, autodiscovery): `POST /conversations/ask` (já existe, ajustado), `GET /conversations`, `GET /conversations/{conversation_id}`.
- **Responses** novos em `src/app/api/responses/`: `ConversationSummaryResponse`, `ConversationDetailResponse`, `MessageResponse`.
- Sem auth de app (protegido por Cloudflare Access na borda, como no M1 seção 9).

### UI web mínima
- `src/app/web/index.html` ganha uma **sidebar** mínima:
  - Ao carregar, chama `GET /conversations` e lista as conversas (título + data).
  - Clique numa conversa: `GET /conversations/{id}` → renderiza os turnos com suas citações; passa a usar aquele `conversation_id` nos próximos envios.
  - Botão "nova conversa": limpa o `conversation_id` corrente.
  - Ao enviar pergunta: manda `{ question, conversation_id }`; ao receber o evento SSE `conversation`, salva o id (persistido em `localStorage` para sobreviver a reload).
- Continua HTML+JS puro, sem framework, sem bundler. Render de citações mantém o escape anti-XSS já introduzido no M1.

---

## 7. Testes

### Unit
- Roundtrip `ConversationMapper` e `MessageMapper` (entity ↔ model attrs), incluindo serialização de `sources` para/de JSONB.
- Lógica de `load_recent`/orçamento de tokens (heurística) com dados sintéticos — corte no budget, ordem cronológica final.
- `AnswerQuestionAction` com fakes: cria/reusa conversa, grava user message, carrega recência, delega ao engine fake; verifica a tupla `(conversation_id, stream)`.
- Regra de ownership/existência (404/403/permite) isolada.

### Integração (banco de teste com pgvector)
- `MessageRepository.append` + `load_recent`: retorna ordem cronológica dentro do budget; respeita o cap de mensagens.
- `ConversationRepository.get_or_create`: idempotente (id existente reusa; `None` cria).
- `POST /conversations/ask` (engine fake/stub): emite evento `conversation`, streama tokens, e **após o stream** os dois turnos (user + assistant, com `sources`) estão persistidos no banco.
- `GET /conversations` filtra por `user_email`; `GET /conversations/{id}` devolve os turnos com citações.
- Ajustar o teste M1 `tests/integration/api/test_ask_endpoint.py` ao novo contrato (sem `history`, com `conversation_id`).

---

## 8. Compatibilidade & migração

- **Breaking change** no contrato do `POST /conversations/ask`: some o campo `history`, entra `conversation_id`. Atualizar UI e testes existentes. Aceitável — é o objetivo do milestone.
- Migration `0002` é aditiva (tabelas novas); não toca em `documents`/`document_chunks`.

---

## 9. Fora de escopo (M3+)

- Summarizer / destilação de fatos (`SummarizeConversationJob`) — M3.
- Memória semântica (fatos/perfil em vetor) recuperada junto ao RAG — M3.
- Rename/delete de conversa pela UI — futuro (YAGNI no M2).
- Validação real do JWT do Cloudflare Access — milestone de auth.
- Precisão de contagem de tokens (tiktoken) e LLMOps/eval — M4.

---

## Roadmap (contexto)

1. **M1 (feito):** fatia vertical — RAG(Notion+web) → resposta citada, streaming, UI mínima.
2. **M2 (este):** memória episódica — persistir turnos, servidor como fonte da verdade, recência por orçamento de tokens, retomar conversas.
3. **M3 — Memória semântica + Summarizer.**
4. **M4 — LLMOps** (trace → eval → gate → release).

# Spec — Agente Oráculo (MVP v1)

**Data:** 2026-07-02
**Status:** aprovado (desenho); pendente plano de implementação
**ADRs relacionados:** [0007](../../adr/0007-agent-framework-pydantic-ai.md) (Pydantic AI), [0008](../../adr/0008-rag-hibrido-pgvector-mcp.md) (RAG híbrido + pgvector), [0009](../../adr/0009-streaming-sse.md) (SSE)

## Objetivo

Chat onde mentorados fazem perguntas sobre o ecossistema tech global e o profissional global de tecnologia, e recebem respostas **confiáveis, amigáveis e sempre com citação de fontes**, fundamentadas **exclusivamente em fontes aprovadas** (Notion via MCP) e **web search** com atribuição.

## Escopo

**Dentro da v1**
- Q&A conversacional com histórico (threads persistidas).
- RAG híbrido sobre docs aprovados do Notion (pgvector) + `fetch` MCP sob demanda.
- Web search com citação (Tavily).
- Seleção de provedor de LLM (Claude/GPT) via `LLM_PROVIDER`.
- Streaming das respostas via SSE, com fontes no final.
- Guardrails: só responde de fontes citáveis/aprovadas; honestidade ("não está na base"); isolamento de conteúdo de tools contra prompt injection.

**Fora da v1 (fast-follow)**
- Tool de dados de alunos (dados operacionais).
- Autenticação (ponto em aberto — slot preservado, sem implementação).
- Evals automatizadas, observabilidade (Langfuse), feedback 👍/👎, roteador de intenção, relatório de lacunas de conteúdo, multi-idioma explícito.

## Arquitetura (encaixe nas camadas)

```
app/api        POST /conversations, POST /conversations/{id}/messages (SSE), GET /conversations/{id}
   │
domain/conversations   AnswerQuestionAction  (orquestra: histórico → motor → persiste turno)
   │                    Conversation, Message (entities/models/mapper/repo)
   │
domain/documents       SyncFromNotionAction, retrieval service (pgvector)
   │                    Document, DocumentChunk (entities/models/mapper/repo)
   │
support/agent          Motor Pydantic AI: Agent + tools + system prompt + seleção de modelo
support/clients        notion (MCP), llm (Claude/GPT já existe), tavily (web search), embeddings (OpenAI)
domain/shared          Citation (value object)
```

Fronteira: o motor Pydantic AI fica em `support/agent/`; `AnswerQuestionAction` o consome por uma interface fina (o domínio não importa o framework diretamente).

## Modelo de dados (novo)

- **`documents`** (já previsto): metadados da página aprovada (notion_page_id, title, source_url, status, last_edited_time).
- **`document_chunks`** (novo): `uuid`, `document_uuid` (FK), `chunk_index`, `content` (Text), `embedding` (`vector(1536)`), timestamps. Índice ANN (ivfflat/hnsw) sobre `embedding`.
- **`conversations`** (novo): `uuid`, título/label opcional, (futuro) `user_ref`, timestamps.
- **`messages`** (novo): `uuid`, `conversation_uuid` (FK), `role` (user|assistant), `content` (Text), `citations` (JSONB), timestamps.
- Migration extra: `CREATE EXTENSION IF NOT EXISTS vector`.

## Componentes e responsabilidades

### 1. Ingestão (documents)
- `SyncFromNotionAction`: lista páginas aprovadas via MCP → para cada uma, chunk (tamanho/overlap por settings) → embeddings (OpenAI `text-embedding-3-small`) → upsert em `document_chunks`. Incremental por `last_edited_time`. Remove chunks órfãos de páginas não mais aprovadas.
- `SyncKnowledgeBaseJob`: chama a Action; idempotente (advisory lock já provido pela base `Job`).

### 2. Retrieval (documents)
- `KnowledgeRetrievalService` (Domain Service): embedda a query, busca top-k no pgvector, devolve chunks + metadados de fonte para citação. Parametrizado por `RAG_TOP_K`.

### 3. Motor do agente (support/agent)
- Configura o `Agent` do Pydantic AI com o modelo resolvido por `LLM_PROVIDER`.
- **Tools:**
  - `search_knowledge_base(query)` → usa `KnowledgeRetrievalService`.
  - `fetch_notion_page(page_id)` → `NotionClient` (MCP), página completa.
  - `web_search(query)` → `TavilyClient`, resultados + URLs.
- **System prompt:** persona do oráculo; regras de grounding e citação; recusa de confidencial/fora de escopo; honestidade; conteúdo de tools marcado como dado não-confiável (anti-injection).
- **Saída:** texto + lista de `Citation` (derivada das tools efetivamente usadas).

### 4. Conversa (conversations)
- `AnswerQuestionAction.execute(conversation_id, question)`: carrega histórico → chama o motor → persiste `message` do usuário e do assistente (com citações) → retorna stream + citações.

### 5. API (app/api)
- `POST /conversations` → cria thread (`ConversationResponse`).
- `POST /conversations/{id}/messages` → `AskQuestionRequest`; resposta **SSE** (`text/event-stream`): tokens + evento final com fontes.
- `GET /conversations/{id}` → histórico.
- Slot de auth no router (dependency), sem implementação.

## Novas dependências (aprovadas nos ADRs)
`pydantic-ai`, `pgvector` (+ integração SQLAlchemy), `tavily-python`. Embeddings via SDK `openai` (já instalado).

## Novas settings
`EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-small`, `EMBEDDING_DIM=1536`, `TAVILY_API_KEY`, `RAG_TOP_K=6`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`.

## Fases sugeridas de implementação
1. **Fundação de dados:** settings novas + extensão pgvector + models/migrations (`document_chunks`, `conversations`, `messages`) + `Citation` VO.
2. **Ingestão:** clients embeddings + chunking + `SyncFromNotionAction` + `SyncKnowledgeBaseJob` (depende do transporte MCP do NotionClient).
3. **Retrieval + motor:** `KnowledgeRetrievalService` + `support/agent` (Pydantic AI) + tool `search_knowledge_base` + `web_search` (Tavily) + `fetch_notion_page`.
4. **Conversa + API:** `conversations` (entities/models/repo/mapper) + `AnswerQuestionAction` + endpoints SSE.
5. **Guardrails + polimento:** system prompt final, anti-injection, recusa de escopo, citação consistente.

## Dependências externas / bloqueios conhecidos
- **Transporte MCP do Notion** (`NotionClient`) ainda é stub — a ingestão real (fase 2) depende de defini-lo (URL/token/tools MCP). O restante (retrieval, motor, API) pode ser desenvolvido e testado com dados de factory enquanto isso.

## Riscos
- Qualidade de retrieval (chunking/top-k) — ajustar por eval manual antes de abrir.
- Prompt injection via conteúdo de Notion/web — isolar conteúdo de tools.
- Custo/latência — habilitar prompt caching (Claude) do system prompt em iteração seguinte.

## Fora de escopo explícito
Auth concreta, dados de alunos, evals automatizadas, observabilidade, feedback, roteador de intenção — todos fast-follow, não bloqueiam a v1.

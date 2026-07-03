# ADR-0008 — RAG híbrido (pgvector + MCP) e embeddings OpenAI

## Status

Aceito — 2026-07-02.

## Resumo

- **Decisão:** recuperação **híbrida** — busca semântica em **pgvector** (chunks dos docs aprovados do Notion, ingeridos) + **MCP** para buscar a página completa/ao vivo sob demanda. Embeddings: **OpenAI `text-embedding-3-small`** (1536 dims).
- **Aplica-se quando:** for implementar ingestão, retrieval, ou mexer em como o conhecimento chega ao modelo.
- **Regra prática:** para responder, o agente recupera chunks via pgvector (com metadados de fonte para citar) e usa MCP `fetch_notion_page` só quando precisa da página inteira/atualizada. Só docs **aprovados** entram no índice.

---

## Contexto

A base de conhecimento vem do Notion via MCP, e o oráculo precisa **citar fontes** de forma confiável, com boa latência e custo controlado. Três padrões possíveis: MCP-as-tool puro (ao vivo), ingestão+embeddings (RAG clássico), ou híbrido.

Restrições do projeto: só conteúdo **aprovado** pode ser indexado/exposto (regra inegociável 4); já existe Postgres com dual engine e migrations; há um job de sincronização previsto (`SyncKnowledgeBaseJob`).

## Decisão

**RAG híbrido:**

1. **Ingestão** (subdomínio `documents`): páginas aprovadas do Notion → chunking → embeddings → upsert em `document_chunks` (coluna `embedding vector` do pgvector), com referência à página de origem. Sync incremental via `last_edited_time` do Notion, rodado por `SyncKnowledgeBaseJob` (idempotente).
2. **Retrieval semântico:** busca top-k no pgvector, retornando chunks **com metadados de fonte** (page id, título, url) para citação.
3. **MCP sob demanda:** tool `fetch_notion_page` para trazer a página completa/ao vivo quando o chunk não basta.

**Embeddings:** OpenAI `text-embedding-3-small`, 1536 dims, configurável via settings (`EMBEDDING_PROVIDER`/`EMBEDDING_MODEL`/`EMBEDDING_DIM`). Desacoplado do provedor de chat (funciona mesmo usando Claude, que não tem embeddings próprios).

**Infra:** `pgvector` no próprio Postgres — nenhuma infra nova. Extensão habilitada por migration.

## Consequências

**Positivas**
- Rápido, barato e com retrieval de qualidade; citação confiável com metadados de fonte.
- Reusa Postgres/Alembic — zero dependência de vector DB externo.
- Freshness controlada pelo job de sync; MCP cobre o caso "preciso da página inteira agora".

**Negativas / riscos**
- Exige pipeline de ingestão + estratégia de sync incremental e de re-chunking.
- Embeddings acoplam a OpenAI: **trocar de modelo de embedding exige re-embedar** toda a base (dims/mudança de espaço). Mitigação: `EMBEDDING_MODEL`/`EMBEDDING_DIM` em settings e migration de re-index quando trocar.
- Novas dependências (`pgvector`, client de embeddings) — aprovadas nesta decisão.

## Alternativas consideradas

- **Só MCP-as-tool (ao vivo):** rejeitado para o índice — latência, custo de tokens e qualidade de busca dependentes do MCP. (Mantido como complemento sob demanda.)
- **Vector DB externo (Qdrant/Weaviate):** rejeitado — infra desnecessária tendo pgvector.
- **Embeddings Voyage/Cohere:** adiados — Voyage tende a ter retrieval superior, mas adiciona fornecedor/chave/custo; reavaliar se precisão de retrieval virar gargalo.

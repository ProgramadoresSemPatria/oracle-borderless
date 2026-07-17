# ADR-0010 — Transporte da base de conhecimento: MCP server do Notion via cliente `mcp`

## Status

Aceito — 2026-07-14.

## Resumo

- **Decisão:** o app consome o Notion pelo **servidor `@notionhq/notion-mcp-server`** usando o **cliente MCP** já disponível via `pydantic-ai` (lib `mcp`), **não** o SDK REST do Notion. Ingestão chama as tools de forma determinística (`search`, `retrieve-page-markdown`, `get-block-children`); o agente recebe o MCP toolset para fetch ao vivo (ADR-0008). Transporte: **Streamable HTTP** para um sidecar em produção (reusa `NOTION_MCP_URL`/`NOTION_MCP_TOKEN`), **stdio via `npx`** para dev.
- **Aplica-se quando:** for implementar o transporte concreto do `NotionClient` ou mexer em como o conhecimento é buscado do Notion.
- **Regra prática:** buscar páginas via `NotionClient.get_page_markdown()` (que já contorna truncagem) e `search` para listar; nunca chamar a REST API do Notion crua. O token da integração vive no servidor MCP, não espalhado no app.

---

## Contexto

A base de conhecimento vem do Notion (ADR-0008: RAG híbrido pgvector + MCP). O `NotionClient` (`src/support/clients/notion/`) é hoje um stub — o transporte concreto era ponto em aberto (ver `CLAUDE.md`).

Já construímos o pipeline de ingestão em cima do **markdown que o `@notionhq/notion-mcp-server` produz** via `retrieve-page-markdown`:

- `KnowledgeCurationPolicy` — filtra o que vira `Document` a partir de metadados do `search`.
- `NotionMarkupCleaner` — limpa a sintaxe própria desse markdown (`<callout>`, `{toggle}`, `<span color>`, `<table>`…).
- `PageMarkdownAssembler` — contorna a truncagem descendo em `get-block-children` + `retrieve-page-markdown` por bloco.

Esse markdown é um **dialeto do MCP server**, não da REST API do Notion. A escolha de transporte precisa preservar esse investimento.

Restrições: integração conectada por **token interno** (`ntn_…`) no workspace *Borderless Coding LLC*; só conteúdo aprovado (regra inegociável nº 4); `pydantic-ai` já é dependência (ADR-0007) e expõe cliente MCP; `mcp` está presente como transitivo. O `.env` já reserva `NOTION_MCP_URL`/`NOTION_MCP_TOKEN`.

## Decisão

**Consumir o Notion pelo MCP server, via o cliente MCP do `pydantic-ai`.**

1. **Servidor:** `@notionhq/notion-mcp-server`, autenticado com o token da integração.
2. **Cliente:** o `mcp` client (mesma lib que o `pydantic_ai.mcp` usa). Dois modos de consumo sobre a mesma sessão:
   - **Ingestão (determinística):** `SyncKnowledgeBaseJob`/actions chamam `search`, `retrieve-page-markdown`, `get-block-children` diretamente. O `NotionClient` implementa `_fetch_page_markdown` e `_list_child_block_ids` (hoje `NotImplementedError`) chamando essas tools; `get_page_markdown()` já compõe o `PageMarkdownAssembler`.
   - **Agente (ao vivo):** o MCP toolset é exposto ao agente para o fetch sob demanda do ADR-0008.
3. **Transporte:**
   - **Produção:** o `notion-mcp-server` roda como **sidecar** em Streamable HTTP; o app conecta por `NOTION_MCP_URL` (+ `NOTION_MCP_TOKEN` no header). O token da integração fica isolado no sidecar.
   - **Dev:** `stdio` disparando `npx @notionhq/notion-mcp-server` com o token via env; `NOTION_MCP_URL` vazio seleciona esse modo.
4. **Dependência:** promover `mcp` a dependência **explícita** no `pyproject.toml` (hoje transitiva) — sem introduzir fornecedor novo (regra nº 10 respeitada; é a lib que o `pydantic-ai` já traz).

## Consequências

**Positivas**
- Reusa 100% do pipeline já feito (cleaner, assembler, curation) — que depende do markdown do MCP server.
- Sem SDK/fornecedor novo; alinhado ao `pydantic-ai` (ADR-0007), que já fala MCP.
- Token da integração isolado no servidor MCP; app só conhece a URL do sidecar.
- Mesmo servidor serve ingestão determinística e fetch ao vivo do agente.

**Negativas / riscos**
- Sidecar adiciona um componente de deploy (processo Node) — mitigado por container próprio; dev usa stdio sem sidecar.
- Acopla ao formato de markdown do `notion-mcp-server`; se ele mudar o dialeto, o `NotionMarkupCleaner` precisa acompanhar.
- `retrieve-page-markdown` trunca páginas grandes — já tratado pelo `PageMarkdownAssembler`.

## Alternativas consideradas

- **SDK REST do Notion (`notion-client`) direto:** rejeitado. Devolve blocos crus, não o markdown — exigiria reescrever um renderer bloco→markdown e refazer o `NotionMarkupCleaner`/`PageMarkdownAssembler`, jogando fora o trabalho já validado. Ganho nenhum sobre o MCP server, que já faz isso.
- **MCP hospedado `mcp.notion.com`:** rejeitado. Exige OAuth por usuário e **não** aceita bearer token — incompatível com um serviço server-side autenticado por token de integração.
- **Só stdio (npx) também em produção:** adiado. Simples, mas amarra o app a um runtime Node co-localizado e ao ciclo de vida do subprocesso; o sidecar HTTP isola melhor e escala independente.

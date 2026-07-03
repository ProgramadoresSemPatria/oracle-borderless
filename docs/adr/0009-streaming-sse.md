# ADR-0009 — Streaming das respostas do chat via SSE

## Status

Aceito — 2026-07-02.

## Resumo

- **Decisão:** as respostas do chat são transmitidas por **Server-Sent Events (SSE)**, via `StreamingResponse` do FastAPI.
- **Aplica-se quando:** for implementar o endpoint de perguntas do chat ou a entrega de respostas ao cliente.
- **Regra prática:** `POST /conversations/{id}/messages` responde com `text/event-stream`, emitindo tokens da resposta e, ao final, um evento com as **fontes/citações**.

---

## Contexto

O chat precisa de resposta em streaming (UX de digitação progressiva). Duas opções principais: SSE (unidirecional servidor→cliente) ou WebSocket (bidirecional). O MVP é pergunta→resposta, sem necessidade de canal bidirecional intenso.

## Decisão

Usar **SSE** com `StreamingResponse`. Formato: eventos de texto (tokens) durante a geração + um evento final estruturado com as citações (fonte Notion/web, título, url, trecho).

## Consequências

**Positivas**
- Simples de implementar e operar com FastAPI; escala bem atrás de proxies HTTP comuns.
- Suficiente para pergunta→resposta com citação.

**Negativas / riscos**
- Unidirecional: cancelamento/entrada ao vivo bidirecional não são nativos (contornável com endpoint separado de cancelamento).
- Migração futura para WebSocket possível se surgir necessidade de interação bidirecional rica.

## Alternativas consideradas

- **WebSocket:** adiado — mais complexo de operar/escalar; só compensa com interação bidirecional intensa, fora do escopo do MVP.
- **Polling:** rejeitado — UX ruim e ineficiente.

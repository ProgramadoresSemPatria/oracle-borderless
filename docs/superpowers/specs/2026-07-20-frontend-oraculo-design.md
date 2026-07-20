# Design — Frontend do Oracle Borderless

- **Data:** 2026-07-20
- **Status:** Aprovado (aguardando revisão da spec)
- **Escopo:** Produto web completo (landing + Sobre & Fontes + Base de conhecimento + App de chat do oráculo), a partir dos designs gerados pelo "Claude design".

## Objetivo

Construir o frontend do Oracle Borderless como um projeto independente, isolado do backend FastAPI, fiel aos screenshots aprovados. Toda a UI em **pt-BR**, **tema escuro** amostrado da logo. O front consome o contrato REST/SSE real do backend e roda também 100% standalone via **modo demo**.

## Decisões de stack (travadas no brainstorming)

| Decisão | Escolha |
|---|---|
| Framework | **React 19 + TypeScript + Vite** |
| Roteamento | **react-router-dom** |
| Estilo | **CSS Modules por componente + `tokens.css`** (variáveis CSS globais). Sem Tailwind. |
| Dados | **Contrato real + modo demo** — interface única, alterna por `VITE_DEMO_MODE`. |
| Logo | **`logo.svg` recriado fielmente** (monograma roxo+verde com gradientes); overridável por arquivo oficial em `src/assets/`. |
| Testes | **Vitest + React Testing Library** nos pontos com lógica (parser SSE, `useAskStream`, `demoStream`, sanitização de URL). |

## Localização e isolamento

Diretório **`frontend/`** na raiz do repo, totalmente separado de `src/` (backend). Toolchain própria (`package.json`, `vite.config.ts`, `tsconfig.json`, `.env`). O backend segue servindo o `index.html` atual sem alteração; o novo front é independente e fala com a API por HTTP. Servir o `frontend/dist` em produção (via FastAPI static ou host dedicado) é decisão de deploy, fora do escopo deste design.

## Árvore de pastas

```
frontend/
├── index.html · package.json · vite.config.ts · tsconfig.json
├── .env.example                  # VITE_API_BASE_URL, VITE_DEMO_MODE
├── public/                       # favicon (derivado da logo)
└── src/
    ├── main.tsx                  # bootstrap React + router
    ├── App.tsx                   # definição das rotas
    ├── assets/
    │   └── logo.svg              # logo recriada (override: logo.png oficial)
    ├── styles/
    │   ├── tokens.css            # cores/gradientes da logo, espaçamento, tipografia, radii
    │   ├── reset.css
    │   └── global.css
    ├── lib/
    │   ├── api/
    │   │   ├── client.ts         # fetch base + baseURL (VITE_API_BASE_URL)
    │   │   ├── conversations.ts  # listConversations, getConversation, askStream
    │   │   └── sse.ts            # parser de SSE sobre fetch + ReadableStream
    │   ├── types.ts              # Conversation, Message, Citation (espelham o contrato)
    │   └── demo/
    │       ├── demoData.ts       # conversas/mensagens/docs de exemplo (dos screenshots)
    │       └── demoStream.ts     # streaming token-a-token simulado + estado de erro
    ├── data/
    │   └── source.ts             # escolhe api vs demo por VITE_DEMO_MODE (mesma interface)
    ├── hooks/
    │   ├── useConversations.ts   # lista + refresh após turno
    │   ├── useConversation.ts    # carrega histórico de uma conversa
    │   └── useAskStream.ts       # máquina de estados do streaming (pensando/streaming/sources/done/error)
    ├── components/               # compartilhados
    │   ├── Logo/                 # <Logo/> referenciando assets/logo.svg
    │   ├── Button/
    │   ├── Header/               # header público (landing/sobre/base)
    │   ├── Footer/
    │   ├── Badge/                # chips (ex.: "Fonte única da verdade", status)
    │   └── SourceTypeTag/        # tag SOP/SIST/VAGA · NOTION
    └── features/
        ├── landing/
        │   ├── LandingPage.tsx
        │   └── components/       # Hero, ComoFunciona, Diferenciais, CtaFinal
        ├── about/
        │   └── AboutPage.tsx     # Sobre & Fontes (cards + "fluxo do conhecimento" + aviso Restrito)
        ├── knowledge/
        │   └── KnowledgePage.tsx # Base de conhecimento (tabela de docs só-leitura + aviso Restrito)
        └── chat/
            ├── ChatPage.tsx
            └── components/
                ├── Sidebar.tsx           # histórico + "Nova conversa", colapsável no mobile
                ├── ConversationList.tsx
                ├── MessageList.tsx
                ├── MessageBubble.tsx     # bolha user (roxa) / oráculo
                ├── CitationCard.tsx      # card de citação expansível [n]
                ├── CitationsBlock.tsx    # "N fontes citadas" + lista
                ├── Composer.tsx          # input fixo "Faça sua pergunta..."
                ├── EmptyState.tsx        # boas-vindas + chips de exemplo (inclui "Ver o estado de erro")
                ├── ThinkingIndicator.tsx # indicador "pensando"
                └── ErrorState.tsx        # mensagem amigável + "Tentar novamente"
```

## Rotas

| Rota | Tela |
|---|---|
| `/` | Landing |
| `/sobre` | Sobre & Fontes |
| `/base` | Base de conhecimento |
| `/oraculo` | App de chat (estado vazio) |
| `/oraculo/:conversationId` | App de chat com conversa aberta |

## Contrato da API (espelhado do backend)

Fonte: `src/app/api/controllers/conversation_controller.py` e `responses/conversation_responses.py`.

- `POST /conversations/ask` — body `{ question: string, conversation_id?: string }`. Resposta **SSE** (`text/event-stream`), eventos em ordem:
  - `conversation` → `{ id }`
  - `token` → `{ text }` (vários; concatenar)
  - `sources` → `{ citations: Citation[] }`
  - `error` → `{ message }` (em falha)
  - `done` → `{}`
- `GET /conversations` → `{ id, title, updated_at }[]`
- `GET /conversations/{id}` → `{ id, title, messages: { role: "user"|"assistant", content, sources?: Citation[] }[] }`

`Citation = { source_type, title, url, snippet, page_id? }`

**Nota de transporte:** `/ask` é POST com corpo SSE, logo `EventSource` (só GET) **não** serve. O client usa `fetch` + `response.body.getReader()` + `TextDecoder`, dividindo por `\n\n` e parseando `event:`/`data:` — mesmo mecanismo do `index.html` atual.

## Fluxo de dados

`data/source.ts` expõe a interface única consumida pelas telas:

```ts
listConversations(): Promise<ConversationSummary[]>
getConversation(id: string): Promise<ConversationDetail>
askStream(input: { question: string; conversationId?: string }): AsyncStream<AskEvent>
```

Por baixo, escolhe entre `lib/api/*` (backend real) e `lib/demo/*` (mock) conforme `VITE_DEMO_MODE`. As telas nunca sabem qual está ativo.

`useAskStream` consome `askStream` e expõe a máquina de estados visual:

```
idle → thinking (antes do 1º token)
     → streaming (concatena tokens; cursor piscando)
     → sources (popula cards de citação)
     → done
     → error (a qualquer momento) → mostra ErrorState + "Tentar novamente"
```

No modo demo, o chip **"Ver o estado de erro"** dispara um `askStream` que emite `error` de propósito, permitindo reproduzir o estado sem backend.

## Tema e identidade visual

`tokens.css` com variáveis amostradas da logo:

- Violeta primário `#5B27E0` → índigo `#3A1E9E`
- Esmeralda `#2FE0A6` → teal `#1CB98A`
- Índigo profundo `#241C63` (mistura)
- Fundos: `#0B0B0D` / superfícies `#14141A`, `#1C1C24`
- Texto: `#F5F5F7` / secundário `#A0A0AB`
- Acentos e CTAs usam gradiente violeta→verde; **tema escuro only**.

Logo como componente `<Logo/>` apontando para `assets/logo.svg` (recriação fiel; overridável pelo arquivo oficial).

## Estados de suporte (chat)

- **Vazio:** logo + "Olá! Pergunte qualquer coisa." + chips de exemplo por categoria (GROWTH/CULTURA/OPERAÇÃO/DEMO).
- **Pensando:** indicador antes do 1º token.
- **Streaming:** cursor piscando ao fim do texto parcial.
- **Erro:** mensagem amigável + "Tentar novamente" (reenvia a última pergunta).

## Testes

Vitest + React Testing Library, focados em lógica (não pixel):

- `lib/api/sse.ts` — parser: eventos fragmentados entre chunks, múltiplos `data:`, ordem.
- `hooks/useAskStream.ts` — transições thinking → streaming → sources → done e o ramo de erro.
- `lib/demo/demoStream.ts` — emite tokens e o caminho de erro.
- Sanitização de URL das citações — só `http`/`https` viram link (mantém a proteção do `index.html` atual).

Fidelidade visual aos screenshots é conferida rodando o app (`vite dev`), não por teste automatizado.

## Ponto em aberto (fast-follow, fora do MVP do front)

Identidade do usuário no header (`duanne@mail.com`) vem do header `cf-access-authenticated-user-email` injetado pelo Cloudflare na borda — o JS do browser não o lê e não há endpoint que o exponha hoje. Neste design: em demo, e-mail placeholder; em produção, um único ponto `getCurrentUser()` pronto para plugar quando existir um endpoint (ex.: `/me`). Wiring real depende do backend.

## Não-objetivos

- Não alterar o backend nem o `index.html` atual.
- Não implementar autenticação no front (é na borda).
- Sem SSR/framework de meta (Next/Nuxt) — SPA Vite basta.
- Sem testes de pixel/visuais automatizados.

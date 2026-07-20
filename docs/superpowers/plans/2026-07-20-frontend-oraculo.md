# Oracle Borderless Web Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Oracle Borderless web product (landing, About & Sources, Knowledge base, and the Oracle chat app) as a standalone React SPA that consumes the backend's REST/SSE contract and also runs fully offline in a demo mode.

**Architecture:** A `frontend/` project isolated from the FastAPI backend. A single data-source abstraction (`data/source.ts`) hides whether calls hit the real API (`lib/api/*`) or the demo mock (`lib/demo/*`), switched by `VITE_DEMO_MODE`. React Router drives four routes; features are organized by screen; a `tokens.css` design system sampled from the logo styles everything (dark theme only).

**Tech Stack:** React 19, TypeScript, Vite, react-router-dom, CSS Modules, Vitest + React Testing Library.

## Global Constraints

- Language: routes, function names, types, components, and file names in **English**; all **user-visible text in pt-BR**.
- Theme: **dark only**, colors sampled from the logo (see tokens below).
- Do **not** modify the backend or `src/app/web/index.html`.
- No auth in the frontend (handled at the Cloudflare edge).
- No SSR / meta-framework — plain Vite SPA.
- `/conversations/ask` is **POST returning SSE** → consume with `fetch` + `ReadableStream`, never `EventSource`.
- Citation URLs: only `http`/`https` become clickable links.
- Design tokens (verbatim):
  - `--violet: #5B27E0`, `--indigo: #3A1E9E`, `--indigo-deep: #241C63`
  - `--emerald: #2FE0A6`, `--teal: #1CB98A`
  - `--bg: #0B0B0D`, `--surface-1: #14141A`, `--surface-2: #1C1C24`
  - `--text: #F5F5F7`, `--text-muted: #A0A0AB`
  - `--gradient: linear-gradient(135deg, var(--violet), var(--emerald))`

## API contract (mirror exactly)

- `POST /conversations/ask` body `{ question: string, conversation_id?: string }` → SSE events, in order: `conversation {id}`, `token {text}` (many), `sources {citations}`, `done {}`; `error {message}` on failure.
- `GET /conversations` → `{ id, title, updated_at }[]`
- `GET /conversations/{id}` → `{ id, title, messages: { role, content, sources? }[] }`
- `Citation = { source_type, title, url, snippet, page_id? }`

---

### Task 1: Scaffold the Vite + React + TS project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`, `frontend/.gitignore`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/vite-env.d.ts`

**Interfaces:**
- Produces: a bootable SPA shell with react-router mounted; `App` renders `<Routes>` with a placeholder per route.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "oracle-borderless-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.ts`**

```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/conversations": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
```

- [ ] **Step 3: Create `frontend/tsconfig.json` and `frontend/tsconfig.node.json`**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `frontend/index.html`, `.gitignore`, `.env.example`, `vite-env.d.ts`**

`frontend/index.html`:
```html
<!doctype html>
<html lang="pt-br">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Oracle Borderless</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/.gitignore`:
```
node_modules
dist
*.local
.env
```

`frontend/.env.example`:
```
VITE_API_BASE_URL=
VITE_DEMO_MODE=true
```

`frontend/src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_DEMO_MODE: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 5: Create `frontend/src/main.tsx` and `frontend/src/App.tsx`**

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/reset.css";
import "./styles/tokens.css";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
```

`frontend/src/App.tsx` (placeholders replaced in later tasks):
```tsx
import { Routes, Route } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<div>Landing</div>} />
      <Route path="/about" element={<div>About</div>} />
      <Route path="/knowledge" element={<div>Knowledge</div>} />
      <Route path="/oracle" element={<div>Oracle</div>} />
      <Route path="/oracle/:conversationId" element={<div>Oracle</div>} />
    </Routes>
  );
}
```

Note: `styles/*` files are created in Task 5; create empty placeholder files now so imports resolve:
```bash
mkdir -p frontend/src/styles && touch frontend/src/styles/reset.css frontend/src/styles/tokens.css frontend/src/styles/global.css
```

- [ ] **Step 6: Install and verify boot**

Run:
```bash
cd frontend && npm install && npm run build
```
Expected: install succeeds; `tsc -b && vite build` completes with no type errors and emits `dist/`.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "chore(frontend): scaffold Vite + React + TS SPA shell"
```

---

### Task 2: Domain types, API client, and SSE parser (TDD)

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api/sse.ts`
- Create: `frontend/src/lib/api/client.ts`
- Create: `frontend/src/lib/api/conversations.ts`
- Create: `frontend/src/test/setup.ts`
- Test: `frontend/src/lib/api/sse.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Citation`, `MessageRole = "user" | "assistant"`, `Message { role: MessageRole; content: string; sources?: Citation[] }`, `ConversationSummary { id: string; title: string | null; updatedAt: string }`, `ConversationDetail { id: string; title: string | null; messages: Message[] }`, `AskInput { question: string; conversationId?: string }`, and the streamed event union `AskEvent = { type: "conversation"; id: string } | { type: "token"; text: string } | { type: "sources"; citations: Citation[] } | { type: "error"; message: string } | { type: "done" }`.
  - `sse.ts`: `async function* parseSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<{ event: string; data: string }>`.
  - `api/conversations.ts`: `listConversations()`, `getConversation(id)`, `askStream(input)` — all matching the data-source interface in Task 3.

- [ ] **Step 1: Create `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 2: Write the failing test for the SSE parser**

`frontend/src/lib/api/sse.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { parseSSE } from "./sse";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const out: { event: string; data: string }[] = [];
  for await (const evt of parseSSE(stream)) out.push(evt);
  return out;
}

describe("parseSSE", () => {
  it("parses complete events", async () => {
    const events = await collect(
      streamOf([
        "event: conversation\ndata: {\"id\":\"abc\"}\n\n",
        "event: token\ndata: {\"text\":\"oi\"}\n\n",
      ])
    );
    expect(events).toEqual([
      { event: "conversation", data: '{"id":"abc"}' },
      { event: "token", data: '{"text":"oi"}' },
    ]);
  });

  it("reassembles an event split across chunks", async () => {
    const events = await collect(streamOf(["event: token\nda", 'ta: {"text":"x"}\n\n']));
    expect(events).toEqual([{ event: "token", data: '{"text":"x"}' }]);
  });

  it("ignores a trailing partial event with no terminator", async () => {
    const events = await collect(streamOf(["event: token\ndata: {}"]));
    expect(events).toEqual([]);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/api/sse.test.ts`
Expected: FAIL — `parseSSE` not defined / module not found.

- [ ] **Step 4: Implement `frontend/src/lib/api/sse.ts`**

```ts
/** Parses an SSE byte stream into { event, data } records. */
export async function* parseSSE(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<{ event: string; data: string }> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const record = readEvent(part);
      if (record) yield record;
    }
  }
}

function readEvent(block: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/api/sse.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Create `frontend/src/lib/types.ts`**

```ts
export interface Citation {
  source_type: string;
  title: string;
  url: string;
  snippet: string;
  page_id?: string | null;
}

export type MessageRole = "user" | "assistant";

export interface Message {
  role: MessageRole;
  content: string;
  sources?: Citation[];
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  updatedAt: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  messages: Message[];
}

export interface AskInput {
  question: string;
  conversationId?: string;
}

export type AskEvent =
  | { type: "conversation"; id: string }
  | { type: "token"; text: string }
  | { type: "sources"; citations: Citation[] }
  | { type: "error"; message: string }
  | { type: "done" };
```

- [ ] **Step 7: Create `frontend/src/lib/api/client.ts`**

```ts
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function apiUrl(path: string): string {
  return `${BASE}${path}`;
}

export async function getJSON<T>(path: string): Promise<T> {
  const resp = await fetch(apiUrl(path));
  if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
  return (await resp.json()) as T;
}
```

- [ ] **Step 8: Create `frontend/src/lib/api/conversations.ts`**

```ts
import type {
  AskEvent,
  AskInput,
  Citation,
  ConversationDetail,
  ConversationSummary,
} from "../types";
import { apiUrl, getJSON } from "./client";
import { parseSSE } from "./sse";

interface SummaryDTO { id: string; title: string | null; updated_at: string; }
interface MessageDTO { role: "user" | "assistant"; content: string; sources?: Citation[] | null; }
interface DetailDTO { id: string; title: string | null; messages: MessageDTO[]; }

export async function listConversations(): Promise<ConversationSummary[]> {
  const rows = await getJSON<SummaryDTO[]>("/conversations");
  return rows.map((r) => ({ id: r.id, title: r.title, updatedAt: r.updated_at }));
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const dto = await getJSON<DetailDTO>(`/conversations/${id}`);
  return {
    id: dto.id,
    title: dto.title,
    messages: dto.messages.map((m) => ({
      role: m.role,
      content: m.content,
      sources: m.sources ?? undefined,
    })),
  };
}

export async function* askStream(input: AskInput): AsyncGenerator<AskEvent> {
  const resp = await fetch(apiUrl("/conversations/ask"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: input.question, conversation_id: input.conversationId ?? null }),
  });
  if (!resp.ok || !resp.body) {
    yield { type: "error", message: `Falha na requisição (${resp.status})` };
    return;
  }
  for await (const { event, data } of parseSSE(resp.body)) {
    const payload = safeParse(data);
    if (event === "conversation") yield { type: "conversation", id: payload.id };
    else if (event === "token") yield { type: "token", text: payload.text };
    else if (event === "sources") yield { type: "sources", citations: payload.citations ?? [] };
    else if (event === "error") yield { type: "error", message: payload.message ?? "erro" };
    else if (event === "done") yield { type: "done" };
  }
}

function safeParse(data: string): any {
  try { return JSON.parse(data); } catch { return {}; }
}
```

- [ ] **Step 9: Type-check and commit**

Run: `cd frontend && npx tsc -b`
Expected: no errors.
```bash
git add frontend/src/lib frontend/src/test
git commit -m "feat(frontend): add domain types, API client, and SSE parser"
```

---

### Task 3: Data source abstraction + demo data + demo stream (TDD)

**Files:**
- Create: `frontend/src/lib/demo/demoData.ts`
- Create: `frontend/src/lib/demo/demoStream.ts`
- Create: `frontend/src/data/source.ts`
- Create: `frontend/src/lib/utils/safeUrl.ts`
- Test: `frontend/src/lib/demo/demoStream.test.ts`
- Test: `frontend/src/lib/utils/safeUrl.test.ts`

**Interfaces:**
- Consumes: types from Task 2; `askStream/listConversations/getConversation` from `lib/api/conversations.ts`.
- Produces:
  - `safeUrl(url: string): string | null` — returns the URL only if `http`/`https`, else `null`.
  - `demoData`: `DEMO_CONVERSATIONS: ConversationSummary[]`, `DEMO_DETAILS: Record<string, ConversationDetail>`, `DEMO_DOCUMENTS: KnowledgeDoc[]` where `KnowledgeDoc = { id: string; code: string; kind: "SOP"|"SIST"|"VAGA"; title: string; origin: string; version: string | null; syncedAt: string; status: "active"|"syncing" }`.
  - `demoStream(input: AskInput): AsyncGenerator<AskEvent>` — emits `conversation`, several `token`s, `sources`, `done`; if `input.question` contains the sentinel `"[demo-error]"`, emits `conversation` then `error` then `done`.
  - `source.ts`: re-exports `listConversations`, `getConversation`, `askStream` picking demo vs api by `import.meta.env.VITE_DEMO_MODE === "true"`.

- [ ] **Step 1: Write failing test for `safeUrl`**

`frontend/src/lib/utils/safeUrl.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { safeUrl } from "./safeUrl";

describe("safeUrl", () => {
  it("accepts http and https", () => {
    expect(safeUrl("https://notion.so/x")).toBe("https://notion.so/x");
    expect(safeUrl("http://notion.so/x")).toBe("http://notion.so/x");
  });
  it("rejects other schemes and garbage", () => {
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("not a url")).toBeNull();
    expect(safeUrl("")).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd frontend && npx vitest run src/lib/utils/safeUrl.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/lib/utils/safeUrl.ts`**

```ts
export function safeUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") return parsed.href;
    return null;
  } catch {
    return null;
  }
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend && npx vitest run src/lib/utils/safeUrl.test.ts`
Expected: PASS.

- [ ] **Step 5: Create `frontend/src/lib/demo/demoData.ts`**

Content mirrors the approved screenshots. Full file:
```ts
import type { Citation, ConversationDetail, ConversationSummary } from "../types";

export interface KnowledgeDoc {
  id: string;
  code: string;
  kind: "SOP" | "SIST" | "VAGA";
  title: string;
  origin: string;
  version: string | null;
  syncedAt: string;
  status: "active" | "syncing";
}

const META_CITATIONS: Citation[] = [
  {
    source_type: "SOP",
    title: "SOP-GM-06 — Nomenclatura de Campanhas e Conjuntos de Anúncios",
    url: "https://www.notion.so/sop-gm-06",
    snippet: "Campanha: [🔥/❄] [Tipo] - [Funil]…",
    page_id: "sop-gm-06",
  },
  {
    source_type: "SOP",
    title: "SOP-GM-04 — UTM Convention & Rastreamento de Tráfego",
    url: "https://www.notion.so/sop-gm-04",
    snippet: "Padrão de UTMs por campanha e origem…",
    page_id: "sop-gm-04",
  },
];

export const DEMO_CONVERSATIONS: ConversationSummary[] = [
  { id: "c1", title: "Nomenclatura de campanhas no Meta Ads", updatedAt: "2026-07-20T10:00:00Z" },
  { id: "c2", title: "Como funciona a Review Mensal (1:1)?", updatedAt: "2026-07-19T10:00:00Z" },
  { id: "c3", title: "Processo de upload no YouTube", updatedAt: "2026-07-18T10:00:00Z" },
  { id: "c4", title: "Detalhes da vaga de Lead Engineer", updatedAt: "2026-07-12T10:00:00Z" },
];

export const DEMO_DETAILS: Record<string, ConversationDetail> = {
  c1: {
    id: "c1",
    title: "Nomenclatura de campanhas no Meta Ads",
    messages: [
      { role: "user", content: "Qual é a nomenclatura oficial de campanhas no Meta Ads?" },
      {
        role: "assistant",
        content:
          "A nomenclatura oficial está no SOP-GM-06 e usa uma estrutura de três níveis:\n\n" +
          "1. Campanha — [🔥 ou ❄] [Tipo] - [Funil]. O símbolo de temperatura (quente/frio) é obrigatório.\n" +
          "2. Conjunto de anúncios — [Verba Diária] - [Público] - [Nome/Tema], com a verba sempre no formato R$ XX/dia e atualizada sempre que mudar.\n" +
          "3. Anúncio — [Nome do Editor] - [Nome do Anúncio].\n\n" +
          "O owner operacional é o Nathan (Tráfego Pago) e o GOM aprova. Quer que eu detalhe os erros comuns listados no SOP?",
        sources: META_CITATIONS,
      },
    ],
  },
};

export const DEMO_DOCUMENTS: KnowledgeDoc[] = [
  { id: "d1", code: "SOP", kind: "SOP", title: "SOP-GM-06 — Nomenclatura de Campanhas e Conjuntos de Anúncios", origin: "Notion · Central do GOM", version: "v1.0", syncedAt: "2026-07-18", status: "active" },
  { id: "d2", code: "SOP", kind: "SOP", title: "SOP-CR-05 — Upload de Vídeo Semanal no YouTube", origin: "Notion · Creative", version: "v1.0", syncedAt: "2026-07-17", status: "active" },
  { id: "d3", code: "SIST", kind: "SIST", title: "Borderless Feedback & 1:1 System", origin: "Notion · Central do GOM", version: "v2.0", syncedAt: "2026-07-15", status: "active" },
  { id: "d4", code: "SOP", kind: "SOP", title: "SOP-GM-05 — Webinário Multi-Sessão Evergreen", origin: "Notion · Growth", version: "v1.0", syncedAt: "2026-07-12", status: "active" },
  { id: "d5", code: "SOP", kind: "SOP", title: "SOP-GM-04 — UTM Convention & Rastreamento de Tráfego", origin: "Notion · Growth", version: null, syncedAt: "2026-07-12", status: "active" },
  { id: "d6", code: "VAGA", kind: "VAGA", title: "Lead Engineer — Systems & Web (Role & Vaga)", origin: "Notion · Hiring Pipeline", version: "v1.0", syncedAt: "2026-07-09", status: "syncing" },
  { id: "d7", code: "SOP", kind: "SOP", title: "SOP-CR-04 — YouTube Roteiro System", origin: "Notion · Creative", version: null, syncedAt: "2026-07-02", status: "active" },
];

export const DEMO_ANSWER =
  "A nomenclatura oficial está no SOP-GM-06 e usa uma estrutura de três níveis: campanha, conjunto e anúncio. O símbolo de temperatura (quente/frio) é obrigatório na campanha.";

export const DEMO_ANSWER_CITATIONS = META_CITATIONS;
```

- [ ] **Step 6: Write failing test for `demoStream`**

`frontend/src/lib/demo/demoStream.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { demoStream } from "./demoStream";
import type { AskEvent } from "../types";

async function collect(input: { question: string; conversationId?: string }) {
  const events: AskEvent[] = [];
  for await (const e of demoStream(input)) events.push(e);
  return events;
}

describe("demoStream", () => {
  it("emits conversation, tokens, sources, done on success", async () => {
    const events = await collect({ question: "qual a nomenclatura?" });
    expect(events[0].type).toBe("conversation");
    expect(events.some((e) => e.type === "token")).toBe(true);
    expect(events.some((e) => e.type === "sources")).toBe(true);
    expect(events.at(-1)?.type).toBe("done");
  });

  it("emits an error path for the [demo-error] sentinel", async () => {
    const events = await collect({ question: "[demo-error]" });
    expect(events.some((e) => e.type === "error")).toBe(true);
    expect(events.some((e) => e.type === "token")).toBe(false);
    expect(events.at(-1)?.type).toBe("done");
  });
});
```

- [ ] **Step 7: Run to verify fail**

Run: `cd frontend && npx vitest run src/lib/demo/demoStream.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 8: Implement `frontend/src/lib/demo/demoStream.ts`**

```ts
import type { AskEvent, AskInput } from "../types";
import { DEMO_ANSWER, DEMO_ANSWER_CITATIONS } from "./demoData";

const ERROR_SENTINEL = "[demo-error]";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function* demoStream(input: AskInput): AsyncGenerator<AskEvent> {
  const conversationId = input.conversationId ?? "demo-new";
  yield { type: "conversation", id: conversationId };

  if (input.question.includes(ERROR_SENTINEL)) {
    await delay(400);
    yield { type: "error", message: "Não consegui gerar a resposta agora. Tente novamente." };
    yield { type: "done" };
    return;
  }

  await delay(500); // "thinking" window before first token
  for (const word of DEMO_ANSWER.split(" ")) {
    yield { type: "token", text: word + " " };
    await delay(40);
  }
  yield { type: "sources", citations: DEMO_ANSWER_CITATIONS };
  yield { type: "done" };
}
```

- [ ] **Step 9: Run to verify pass**

Run: `cd frontend && npx vitest run src/lib/demo/demoStream.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 10: Create `frontend/src/data/source.ts`**

```ts
import type { AskInput, ConversationDetail, ConversationSummary } from "../lib/types";
import * as api from "../lib/api/conversations";
import { demoStream } from "../lib/demo/demoStream";
import { DEMO_CONVERSATIONS, DEMO_DETAILS } from "../lib/demo/demoData";

const DEMO = import.meta.env.VITE_DEMO_MODE === "true";

export function listConversations(): Promise<ConversationSummary[]> {
  if (DEMO) return Promise.resolve(DEMO_CONVERSATIONS);
  return api.listConversations();
}

export function getConversation(id: string): Promise<ConversationDetail> {
  if (DEMO) {
    return Promise.resolve(
      DEMO_DETAILS[id] ?? { id, title: null, messages: [] }
    );
  }
  return api.getConversation(id);
}

export function askStream(input: AskInput) {
  return DEMO ? demoStream(input) : api.askStream(input);
}

export const isDemo = DEMO;
```

- [ ] **Step 11: Type-check and commit**

Run: `cd frontend && npx tsc -b`
Expected: no errors.
```bash
git add frontend/src/lib frontend/src/data
git commit -m "feat(frontend): add data-source abstraction, demo data and demo stream"
```

---

### Task 4: Streaming hook + data hooks (TDD for the state machine)

**Files:**
- Create: `frontend/src/hooks/useAskStream.ts`
- Create: `frontend/src/hooks/useConversations.ts`
- Create: `frontend/src/hooks/useConversation.ts`
- Test: `frontend/src/hooks/useAskStream.test.ts`

**Interfaces:**
- Consumes: `askStream`, `listConversations`, `getConversation` from `data/source.ts`; types from Task 2.
- Produces:
  - `useAskStream()` → `{ status: "idle"|"thinking"|"streaming"|"done"|"error"; answer: string; citations: Citation[]; conversationId: string | null; errorMessage: string | null; ask(input: AskInput): Promise<void>; reset(): void }`.
  - `useConversations()` → `{ conversations: ConversationSummary[]; refresh(): Promise<void>; loading: boolean }`.
  - `useConversation(id: string | undefined)` → `{ detail: ConversationDetail | null; loading: boolean }`.

- [ ] **Step 1: Write failing test for `useAskStream`**

`frontend/src/hooks/useAskStream.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { AskEvent } from "../lib/types";

const scenario = { events: [] as AskEvent[] };

vi.mock("../data/source", () => ({
  isDemo: true,
  askStream: async function* () {
    for (const e of scenario.events) yield e;
  },
}));

import { useAskStream } from "./useAskStream";

beforeEach(() => {
  scenario.events = [];
});

describe("useAskStream", () => {
  it("moves through thinking → streaming → done and accumulates tokens + citations", async () => {
    scenario.events = [
      { type: "conversation", id: "c9" },
      { type: "token", text: "olá " },
      { type: "token", text: "mundo" },
      { type: "sources", citations: [{ source_type: "SOP", title: "T", url: "https://x", snippet: "s" }] },
      { type: "done" },
    ];
    const { result } = renderHook(() => useAskStream());
    await act(async () => {
      await result.current.ask({ question: "oi" });
    });
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.answer).toBe("olá mundo");
    expect(result.current.conversationId).toBe("c9");
    expect(result.current.citations).toHaveLength(1);
  });

  it("enters error status on an error event", async () => {
    scenario.events = [
      { type: "conversation", id: "c9" },
      { type: "error", message: "falhou" },
      { type: "done" },
    ];
    const { result } = renderHook(() => useAskStream());
    await act(async () => {
      await result.current.ask({ question: "[demo-error]" });
    });
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("falhou");
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd frontend && npx vitest run src/hooks/useAskStream.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `frontend/src/hooks/useAskStream.ts`**

```ts
import { useCallback, useState } from "react";
import type { AskInput, Citation } from "../lib/types";
import { askStream } from "../data/source";

export type AskStatus = "idle" | "thinking" | "streaming" | "done" | "error";

export function useAskStream() {
  const [status, setStatus] = useState<AskStatus>("idle");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStatus("idle");
    setAnswer("");
    setCitations([]);
    setErrorMessage(null);
  }, []);

  const ask = useCallback(async (input: AskInput) => {
    setStatus("thinking");
    setAnswer("");
    setCitations([]);
    setErrorMessage(null);
    try {
      for await (const evt of askStream(input)) {
        if (evt.type === "conversation") setConversationId(evt.id);
        else if (evt.type === "token") {
          setStatus("streaming");
          setAnswer((prev) => prev + evt.text);
        } else if (evt.type === "sources") setCitations(evt.citations);
        else if (evt.type === "error") {
          setErrorMessage(evt.message);
          setStatus("error");
        } else if (evt.type === "done") {
          setStatus((s) => (s === "error" ? "error" : "done"));
        }
      }
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "erro inesperado");
      setStatus("error");
    }
  }, []);

  return { status, answer, citations, conversationId, errorMessage, ask, reset };
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend && npx vitest run src/hooks/useAskStream.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Implement `frontend/src/hooks/useConversations.ts`**

```ts
import { useCallback, useEffect, useState } from "react";
import type { ConversationSummary } from "../lib/types";
import { listConversations } from "../data/source";

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setConversations(await listConversations());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { conversations, refresh, loading };
}
```

- [ ] **Step 6: Implement `frontend/src/hooks/useConversation.ts`**

```ts
import { useEffect, useState } from "react";
import type { ConversationDetail } from "../lib/types";
import { getConversation } from "../data/source";

export function useConversation(id: string | undefined) {
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!id) {
      setDetail(null);
      return;
    }
    let active = true;
    setLoading(true);
    getConversation(id)
      .then((d) => {
        if (active) setDetail(d);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  return { detail, loading };
}
```

- [ ] **Step 7: Type-check and commit**

Run: `cd frontend && npx tsc -b`
Expected: no errors.
```bash
git add frontend/src/hooks
git commit -m "feat(frontend): add streaming and data hooks"
```

---

### Task 5: Design tokens, global styles, and shared components

**Files:**
- Create: `frontend/src/styles/reset.css`, `frontend/src/styles/tokens.css`, `frontend/src/styles/global.css`
- Create: `frontend/src/assets/logo.svg`
- Create: `frontend/public/favicon.svg`
- Create: `frontend/src/components/Logo/Logo.tsx`, `Logo.module.css`
- Create: `frontend/src/components/Button/Button.tsx`, `Button.module.css`
- Create: `frontend/src/components/Header/Header.tsx`, `Header.module.css`
- Create: `frontend/src/components/Footer/Footer.tsx`, `Footer.module.css`
- Create: `frontend/src/components/Badge/Badge.tsx`, `Badge.module.css`
- Create: `frontend/src/components/SourceTypeTag/SourceTypeTag.tsx`, `SourceTypeTag.module.css`

**Interfaces:**
- Produces:
  - `<Logo size?: number />` — renders `assets/logo.svg` via `<img>`; swap the `src` to `logo.png` if an official file is dropped in `assets/`.
  - `<Button variant?: "primary"|"ghost"|"gradient"; as?: "button"|"link"; to?: string; onClick?; children>`.
  - `<Header />` — public top nav: Logo + "Oracle Borderless" wordmark, links to `/about`, `/knowledge`, and a gradient "Abrir o oráculo →" CTA to `/oracle`.
  - `<Footer />` — "Oracle Borderless · oracle.borderless.dev" left, "Fonte única da verdade · movido a fontes aprovadas" right.
  - `<Badge tone?: "neutral"|"emerald"; children>` — pill with a status dot.
  - `<SourceTypeTag kind: string />` — small monospace tag like `SOP · NOTION`.

- [ ] **Step 1: Create `frontend/src/styles/reset.css`**

```css
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; }
html, body, #root { height: 100%; }
body { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
img, svg { display: block; max-width: 100%; }
a { color: inherit; text-decoration: none; }
button { font: inherit; color: inherit; background: none; border: none; cursor: pointer; }
input, textarea { font: inherit; color: inherit; }
```

- [ ] **Step 2: Create `frontend/src/styles/tokens.css`**

```css
:root {
  /* Brand — sampled from the logo */
  --violet: #5B27E0;
  --indigo: #3A1E9E;
  --indigo-deep: #241C63;
  --emerald: #2FE0A6;
  --teal: #1CB98A;

  /* Surfaces */
  --bg: #0B0B0D;
  --surface-1: #14141A;
  --surface-2: #1C1C24;
  --border: #26262F;

  /* Text */
  --text: #F5F5F7;
  --text-muted: #A0A0AB;

  /* Accents */
  --gradient: linear-gradient(135deg, var(--violet), var(--emerald));
  --violet-soft: rgba(91, 39, 224, 0.16);
  --emerald-soft: rgba(47, 224, 166, 0.14);

  /* Scale */
  --radius-sm: 8px;
  --radius: 14px;
  --radius-lg: 22px;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-8: 48px; --space-10: 72px;
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", monospace;
  --maxw: 1200px;
}
```

- [ ] **Step 3: Create `frontend/src/styles/global.css`**

```css
body {
  font-family: var(--font-sans);
  background: var(--bg);
  color: var(--text);
  background-image:
    radial-gradient(60% 50% at 15% 0%, rgba(91, 39, 224, 0.12), transparent 70%),
    radial-gradient(50% 40% at 100% 100%, rgba(47, 224, 166, 0.08), transparent 70%);
  background-attachment: fixed;
}
h1, h2, h3 { line-height: 1.1; letter-spacing: -0.02em; font-weight: 800; }
.container { max-width: var(--maxw); margin: 0 auto; padding: 0 var(--space-5); }
.text-gradient {
  background: var(--gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.eyebrow { color: var(--emerald); font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; font-size: 0.78rem; }
```

- [ ] **Step 4: Create `frontend/src/assets/logo.svg` and `frontend/public/favicon.svg`**

Faithful recreation of the two-shape monogram (violet + emerald with gradients on a transparent background). Use the same content for both files.
```svg
<svg viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Oracle Borderless">
  <defs>
    <linearGradient id="v" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#6B34F0"/>
      <stop offset="1" stop-color="#3A1E9E"/>
    </linearGradient>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#34E8AD"/>
      <stop offset="1" stop-color="#1CB98A"/>
    </linearGradient>
  </defs>
  <!-- Violet stroke: left stem + top-left hook curving to center -->
  <path fill="url(#v)" d="M336 324h132v300a132 132 0 0 1-132 132V324z"/>
  <path fill="url(#v)" d="M612 324h132v210a132 132 0 0 1-132 132 132 132 0 0 0 0-264V324z" opacity="0.92"/>
  <!-- Emerald stroke: center bowl curving down to the right stem -->
  <path fill="url(#g)" d="M468 420a276 276 0 0 1 276 276h-132a144 144 0 0 0-144-144z"/>
  <path fill="url(#g)" d="M612 540h132v216a132 132 0 0 1-132-132V540z"/>
  <path fill="url(#g)" d="M336 624h132v132a132 132 0 0 1-132-132z" opacity="0.9"/>
</svg>
```
Note: this is an approximation. If the official artwork is added at `frontend/src/assets/logo.png`, change `Logo.tsx`'s import to point at it.

- [ ] **Step 5: Create `frontend/src/components/Logo/Logo.tsx` + CSS**

```tsx
import logoUrl from "../../assets/logo.svg";
import styles from "./Logo.module.css";

export function Logo({ size = 36 }: { size?: number }) {
  return (
    <span className={styles.chip} style={{ width: size, height: size }}>
      <img src={logoUrl} alt="Oracle Borderless" />
    </span>
  );
}
```
`Logo.module.css`:
```css
.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 28%;
  padding: 14%;
}
.chip img { width: 100%; height: 100%; }
```

- [ ] **Step 6: Create `Button`, `Badge`, `SourceTypeTag` components + CSS**

`Button.tsx`:
```tsx
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import styles from "./Button.module.css";

type Props = {
  variant?: "primary" | "ghost" | "gradient";
  to?: string;
  onClick?: () => void;
  children: ReactNode;
};

export function Button({ variant = "primary", to, onClick, children }: Props) {
  const cls = `${styles.btn} ${styles[variant]}`;
  if (to) return <Link className={cls} to={to}>{children}</Link>;
  return <button className={cls} onClick={onClick}>{children}</button>;
}
```
`Button.module.css`:
```css
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 20px; border-radius: var(--radius); font-weight: 700; transition: transform .12s ease, filter .12s ease; }
.btn:hover { transform: translateY(-1px); }
.primary { background: var(--violet); color: #fff; }
.gradient { background: var(--gradient); color: #06231b; box-shadow: 0 10px 30px -12px var(--violet); }
.ghost { background: var(--surface-2); color: var(--text); border: 1px solid var(--border); }
```
`Badge.tsx`:
```tsx
import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "emerald"; children: ReactNode }) {
  return (
    <span className={`${styles.badge} ${styles[tone]}`}>
      <span className={styles.dot} />
      {children}
    </span>
  );
}
```
`Badge.module.css`:
```css
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); font-size: .85rem; color: var(--text-muted); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald); }
.emerald { color: var(--emerald); border-color: rgba(47,224,166,.3); }
```
`SourceTypeTag.tsx`:
```tsx
import styles from "./SourceTypeTag.module.css";

export function SourceTypeTag({ kind }: { kind: string }) {
  return <span className={styles.tag}>{kind.toUpperCase()} · NOTION</span>;
}
```
`SourceTypeTag.module.css`:
```css
.tag { font-family: var(--font-mono); font-size: .68rem; letter-spacing: .08em; padding: 4px 8px; border-radius: 6px; background: var(--violet-soft); color: #c9b6ff; }
```

- [ ] **Step 7: Create `Header` and `Footer` + CSS**

`Header.tsx`:
```tsx
import { Link } from "react-router-dom";
import { Logo } from "../Logo/Logo";
import { Button } from "../Button/Button";
import styles from "./Header.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        <Link to="/" className={styles.brand}>
          <Logo size={40} />
          <span>Oracle <span className="text-gradient">Borderless</span></span>
        </Link>
        <nav className={styles.nav}>
          <Link to="/about">Sobre &amp; Fontes</Link>
          <Link to="/knowledge">Base de conhecimento</Link>
          <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
        </nav>
      </div>
    </header>
  );
}
```
`Header.module.css`:
```css
.header { position: sticky; top: 0; z-index: 10; backdrop-filter: blur(8px); background: rgba(11,11,13,.6); }
.inner { display: flex; align-items: center; justify-content: space-between; height: 76px; }
.brand { display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 1.15rem; }
.nav { display: flex; align-items: center; gap: 28px; color: var(--text-muted); }
.nav a:hover { color: var(--text); }
@media (max-width: 720px) { .nav a { display: none; } }
```
`Footer.tsx`:
```tsx
import { Logo } from "../Logo/Logo";
import styles from "./Footer.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <span className={styles.left}><Logo size={26} /> Oracle Borderless · oracle.borderless.dev</span>
        <span className={styles.right}>Fonte única da verdade · movido a fontes aprovadas</span>
      </div>
    </footer>
  );
}
```
`Footer.module.css`:
```css
.footer { border-top: 1px solid var(--border); margin-top: var(--space-10); padding: var(--space-6) 0; }
.inner { display: flex; align-items: center; justify-content: space-between; color: var(--text-muted); font-size: .9rem; gap: 16px; flex-wrap: wrap; }
.left { display: inline-flex; align-items: center; gap: 10px; }
```

- [ ] **Step 8: Verify build and commit**

Run: `cd frontend && npx tsc -b && npm run dev` (open http://localhost:5173, confirm styles load; Ctrl-C).
Expected: no type errors; dark theme visible.
```bash
git add frontend/src/styles frontend/src/assets frontend/public frontend/src/components
git commit -m "feat(frontend): add design tokens, global styles and shared components"
```

---

### Task 6: Landing page

**Files:**
- Create: `frontend/src/features/landing/LandingPage.tsx`, `LandingPage.module.css`
- Create: `frontend/src/features/landing/components/Hero.tsx`
- Create: `frontend/src/features/landing/components/HowItWorks.tsx`
- Create: `frontend/src/features/landing/components/Differentiators.tsx`
- Create: `frontend/src/features/landing/components/FinalCta.tsx`
- Modify: `frontend/src/App.tsx` (wire `/` to `LandingPage`)

**Interfaces:**
- Consumes: `Header`, `Footer`, `Button`, `Logo`, `Badge`, `SourceTypeTag` from Task 5.
- Produces: `<LandingPage />` (default route element).

Screenshot reference: hero with badge "Fonte única da verdade do ecossistema", headline "Pergunte. Receba a verdade, com as fontes." (last line gradient), subcopy, CTAs "Abrir o oráculo →" (gradient) and "Ver as fontes" (ghost), and a floating chat-preview card. "COMO FUNCIONA" section with 3 numbered cards (01/02/03). Differentiators: 3 gradient-icon cards ("Só fontes liberadas", "Nada confidencial", "Sempre com citação"). Final CTA card with logo + "Pergunte qualquer coisa. Receba a verdade, com as fontes." + gradient button.

- [ ] **Step 1: Implement `Hero.tsx`**

```tsx
import { Badge } from "../../../components/Badge/Badge";
import { Button } from "../../../components/Button/Button";
import { Logo } from "../../../components/Logo/Logo";
import { SourceTypeTag } from "../../../components/SourceTypeTag/SourceTypeTag";
import styles from "../LandingPage.module.css";

export function Hero() {
  return (
    <section className={`container ${styles.hero}`}>
      <div className={styles.heroCopy}>
        <Badge tone="emerald">Fonte única da verdade do ecossistema</Badge>
        <h1 className={styles.headline}>
          Pergunte.<br />Receba a verdade,<br />
          <span className="text-gradient">com as fontes.</span>
        </h1>
        <p className={styles.sub}>
          O Oracle Borderless é um oráculo de IA que responde qualquer pergunta sobre as
          regras e a operação do ecossistema — em linguagem clara e sempre baseado{" "}
          <strong>exclusivamente em documentos aprovados</strong>. Cada resposta cita de onde veio.
        </p>
        <div className={styles.heroCtas}>
          <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
          <Button variant="ghost" to="/about">Ver as fontes</Button>
        </div>
      </div>
      <aside className={styles.previewCard}>
        <header className={styles.previewHead}>
          <Logo size={30} /> <strong>Oráculo</strong>
          <span className={styles.online}>● online</span>
        </header>
        <div className={styles.previewUser}>Qual a nomenclatura de campanhas no Meta Ads?</div>
        <div className={styles.previewBot}>
          A nomenclatura oficial está no <strong>SOP-GM-06</strong> e usa uma estrutura de
          3 níveis: campanha, conjunto e anúncio.
        </div>
        <div className={styles.previewSource}>
          <SourceTypeTag kind="SOP" /> <strong>SOP-GM-06 — Nomenclatura de Campanhas</strong>
        </div>
      </aside>
    </section>
  );
}
```

- [ ] **Step 2: Implement `HowItWorks.tsx`**

```tsx
import styles from "../LandingPage.module.css";

const STEPS = [
  { n: "01", title: "Você pergunta", body: "Em linguagem natural, do jeito que falaria com um colega. Sem sintaxe, sem menu." },
  { n: "02", title: "Busca em fontes aprovadas", body: "O oráculo procura apenas nos documentos liberados do Notion — nada confidencial entra na busca." },
  { n: "03", title: "Resposta citada", body: "Você recebe uma resposta clara e cada afirmação vem com o card da fonte que a sustenta." },
];

export function HowItWorks() {
  return (
    <section className={`container ${styles.section}`}>
      <p className="eyebrow" style={{ textAlign: "center" }}>Como funciona</p>
      <h2 className={styles.sectionTitle}>Da pergunta à verdade, em três passos</h2>
      <div className={styles.grid3}>
        {STEPS.map((s) => (
          <article key={s.n} className={styles.stepCard}>
            <span className={styles.stepNum}>{s.n}</span>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Implement `Differentiators.tsx`**

```tsx
import styles from "../LandingPage.module.css";

const ITEMS = [
  { icon: "✓", title: "Só fontes liberadas", body: "A base vem exclusivamente de documentos aprovados. O que não foi liberado simplesmente não existe para o oráculo." },
  { icon: "⃠", title: "Nada confidencial", body: "Materiais restritos nunca são indexados. Se a informação é sensível, o oráculo não a acessa nem revela." },
  { icon: "◎", title: "Sempre com citação", body: "Toda resposta mostra de onde veio — título, tipo, trecho e link. Confiança verificável, não fé cega." },
];

export function Differentiators() {
  return (
    <section className={`container ${styles.section}`}>
      <div className={styles.grid3}>
        {ITEMS.map((it) => (
          <article key={it.title} className={styles.diffCard}>
            <span className={styles.diffIcon}>{it.icon}</span>
            <h3>{it.title}</h3>
            <p>{it.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Implement `FinalCta.tsx`**

```tsx
import { Button } from "../../../components/Button/Button";
import { Logo } from "../../../components/Logo/Logo";
import styles from "../LandingPage.module.css";

export function FinalCta() {
  return (
    <section className={`container ${styles.section}`}>
      <div className={styles.ctaCard}>
        <Logo size={64} />
        <h2>Pergunte qualquer coisa. Receba a verdade, com as fontes.</h2>
        <p>Sem confidencial, sem achismo. Só o que já está aprovado no ecossistema.</p>
        <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Implement `LandingPage.tsx` and `LandingPage.module.css`**

```tsx
import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Hero } from "./components/Hero";
import { HowItWorks } from "./components/HowItWorks";
import { Differentiators } from "./components/Differentiators";
import { FinalCta } from "./components/FinalCta";

export default function LandingPage() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <HowItWorks />
        <Differentiators />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
```
`LandingPage.module.css` (key rules; refine visually against the screenshot):
```css
.hero { display: grid; grid-template-columns: 1.1fr .9fr; gap: var(--space-8); align-items: center; padding: var(--space-10) var(--space-5); }
.headline { font-size: clamp(2.6rem, 6vw, 5rem); margin: var(--space-4) 0; }
.sub { color: var(--text-muted); font-size: 1.15rem; max-width: 32ch; }
.heroCtas { display: flex; gap: var(--space-3); margin-top: var(--space-5); }
.previewCard { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); display: grid; gap: var(--space-3); }
.previewHead { display: flex; align-items: center; gap: 10px; }
.online { margin-left: auto; color: var(--emerald); font-size: .8rem; }
.previewUser { justify-self: end; background: var(--violet); padding: 12px 16px; border-radius: 14px 14px 4px 14px; max-width: 80%; }
.previewBot { color: var(--text); }
.previewSource { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; display: flex; align-items: center; gap: 10px; font-size: .85rem; }
.section { padding: var(--space-10) var(--space-5); }
.sectionTitle { text-align: center; font-size: clamp(1.8rem, 4vw, 3rem); margin: var(--space-3) 0 var(--space-8); }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-5); }
.stepCard, .diffCard { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-6); }
.stepCard p, .diffCard p { color: var(--text-muted); margin-top: var(--space-3); }
.stepNum { display: inline-flex; padding: 8px 12px; border-radius: 10px; background: var(--violet-soft); color: #c9b6ff; font-family: var(--font-mono); }
.diffIcon { display: inline-flex; width: 48px; height: 48px; align-items: center; justify-content: center; border-radius: 12px; background: var(--gradient); color: #06231b; font-size: 1.3rem; margin-bottom: var(--space-3); }
.ctaCard { text-align: center; background: var(--indigo-deep); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-10); display: grid; justify-items: center; gap: var(--space-4); }
.ctaCard h2 { font-size: clamp(1.6rem, 3.5vw, 2.6rem); max-width: 20ch; }
.ctaCard p { color: var(--text-muted); }
@media (max-width: 900px) { .hero { grid-template-columns: 1fr; } .grid3 { grid-template-columns: 1fr; } }
```

- [ ] **Step 6: Wire the route in `App.tsx`**

Replace the `/` route:
```tsx
import LandingPage from "./features/landing/LandingPage";
// ...
<Route path="/" element={<LandingPage />} />
```

- [ ] **Step 7: Verify and commit**

Run: `cd frontend && npx tsc -b && npm run dev` → open `/`, compare to landing screenshots.
Expected: hero, 3-step, differentiators, final CTA render in dark theme.
```bash
git add frontend/src/features/landing frontend/src/App.tsx
git commit -m "feat(frontend): add landing page"
```

---

### Task 7: About & Sources page

**Files:**
- Create: `frontend/src/features/about/AboutPage.tsx`, `AboutPage.module.css`
- Modify: `frontend/src/App.tsx` (wire `/about`)

**Interfaces:**
- Consumes: `Header`, `Footer`, `Button`.
- Produces: `<AboutPage />`.

Screenshot reference: eyebrow "SOBRE & FONTES", title "De onde vem a verdade do oráculo", intro paragraph, 3 cards ("Aprovado no Notion", "Zero confidencial", "Sempre sincronizado"), a "O fluxo do conhecimento" panel with 4 labeled columns (ORIGEM/FILTRO/ÍNDICE/SAÍDA), an emerald callout about 🔴 Restrito documents, and a "Fazer uma pergunta →" CTA.

- [ ] **Step 1: Implement `AboutPage.tsx`**

```tsx
import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Button } from "../../components/Button/Button";
import styles from "./AboutPage.module.css";

const CARDS = [
  { icon: "✓", title: "Aprovado no Notion", body: "Cada resposta nasce de um documento que alguém do ecossistema liberou. Fonte única da verdade, de verdade." },
  { icon: "⃠", title: "Zero confidencial", body: "Docs 🔴 Restrito e dados sensíveis ficam de fora do índice. O oráculo não tem como acessá-los." },
  { icon: "↻", title: "Sempre sincronizado", body: "Quando um documento aprovado muda no Notion, o oráculo passa a responder pela versão mais recente." },
];

const FLOW = [
  { label: "ORIGEM", title: "Notion", body: "Documentos aprovados do ecossistema (SOPs, sistemas, vagas)." },
  { label: "FILTRO", title: "Só liberados", body: "Confidenciais e restritos são descartados antes de indexar." },
  { label: "ÍNDICE", title: "Base do oráculo", body: "Conteúdo liberado vira a única fonte consultável." },
  { label: "SAÍDA", title: "Resposta citada", body: "Linguagem clara + cards de fonte com trecho e link." },
];

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="container">
        <p className="eyebrow">Sobre &amp; Fontes</p>
        <h1 className={styles.title}>De onde vem a<br />verdade do oráculo</h1>
        <p className={styles.intro}>
          O Oracle Borderless não inventa nem opina. Ele lê apenas os documentos que o
          ecossistema liberou no Notion e responde com base neles — citando cada fonte que usou.
          Se algo não está documentado e aprovado, o oráculo diz que não sabe.
        </p>
        <div className={styles.cards}>
          {CARDS.map((c) => (
            <article key={c.title} className={styles.card}>
              <span className={styles.icon}>{c.icon}</span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </article>
          ))}
        </div>
        <section className={styles.flowPanel}>
          <h2>O fluxo do conhecimento</h2>
          <div className={styles.flowGrid}>
            {FLOW.map((f) => (
              <div key={f.label} className={styles.flowCol}>
                <span className={styles.flowLabel}>{f.label}</span>
                <strong>{f.title}</strong>
                <p>{f.body}</p>
              </div>
            ))}
          </div>
        </section>
        <div className={styles.callout}>
          <span className={styles.calloutCheck}>✓</span>
          <p>Documentos marcados como 🔴 <strong>Restrito</strong> nunca entram no oráculo. Dados operacionais
            (como resultados de alunos) só aparecem quando o documento de origem foi liberado — e sempre com a fonte citada.</p>
        </div>
        <div style={{ margin: "40px 0" }}>
          <Button variant="primary" to="/oracle">Fazer uma pergunta →</Button>
        </div>
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 2: Implement `AboutPage.module.css`**

```css
.title { font-size: clamp(2.2rem, 5vw, 3.6rem); margin: var(--space-4) 0; }
.intro { color: var(--text-muted); font-size: 1.15rem; max-width: 60ch; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-5); margin: var(--space-8) 0; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-6); }
.card p { color: var(--text-muted); margin-top: var(--space-3); }
.icon { display: inline-flex; width: 44px; height: 44px; align-items: center; justify-content: center; border-radius: 12px; background: var(--gradient); color: #06231b; margin-bottom: var(--space-3); }
.flowPanel { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-6); }
.flowGrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-5); margin-top: var(--space-5); }
.flowLabel { font-family: var(--font-mono); font-size: .68rem; letter-spacing: .1em; color: #c9b6ff; }
.flowCol { display: grid; gap: 6px; }
.flowCol p { color: var(--text-muted); font-size: .9rem; }
.callout { display: flex; gap: 14px; align-items: flex-start; margin: var(--space-6) 0; padding: var(--space-5); border-radius: var(--radius); background: var(--emerald-soft); border: 1px solid rgba(47,224,166,.3); }
.calloutCheck { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: 8px; background: var(--emerald); color: #06231b; flex: none; }
@media (max-width: 900px) { .cards { grid-template-columns: 1fr; } .flowGrid { grid-template-columns: 1fr 1fr; } }
```

- [ ] **Step 3: Wire the route and commit**

In `App.tsx`:
```tsx
import AboutPage from "./features/about/AboutPage";
// ...
<Route path="/about" element={<AboutPage />} />
```
Run: `cd frontend && npx tsc -b && npm run dev` → open `/about`, compare to screenshots.
```bash
git add frontend/src/features/about frontend/src/App.tsx
git commit -m "feat(frontend): add About & Sources page"
```

---

### Task 8: Knowledge base page

**Files:**
- Create: `frontend/src/features/knowledge/KnowledgePage.tsx`, `KnowledgePage.module.css`
- Create: `frontend/src/data/documents.ts`
- Modify: `frontend/src/App.tsx` (wire `/knowledge`)

**Interfaces:**
- Consumes: `Header`, `Footer`, `Badge`, `DEMO_DOCUMENTS` + `KnowledgeDoc` from `lib/demo/demoData.ts`.
- Produces:
  - `data/documents.ts`: `listDocuments(): Promise<KnowledgeDoc[]>` — returns `DEMO_DOCUMENTS` in demo mode (no real endpoint exists yet; document this).
  - `<KnowledgePage />`.

Screenshot reference: eyebrow "BASE DE CONHECIMENTO", title "Documentos que alimentam o oráculo", green "Sincronizado com o Notion" badge, read-only note, a table (DOCUMENTO / SINCRONIZAÇÃO / STATUS) with a source tag per row, status dot (green "Ativo", amber "Sincronizando"), and a locked 🔴 Restrito footnote.

- [ ] **Step 1: Create `frontend/src/data/documents.ts`**

```ts
import type { KnowledgeDoc } from "../lib/demo/demoData";
import { DEMO_DOCUMENTS } from "../lib/demo/demoData";

const DEMO = import.meta.env.VITE_DEMO_MODE === "true";

/**
 * There is no backend documents endpoint yet. In demo mode we return the seeded
 * list; when a real `/documents` endpoint exists, branch on !DEMO here.
 */
export function listDocuments(): Promise<KnowledgeDoc[]> {
  if (DEMO) return Promise.resolve(DEMO_DOCUMENTS);
  return Promise.resolve(DEMO_DOCUMENTS);
}
```

- [ ] **Step 2: Implement `KnowledgePage.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Badge } from "../../components/Badge/Badge";
import { SourceTypeTag } from "../../components/SourceTypeTag/SourceTypeTag";
import { listDocuments } from "../../data/documents";
import type { KnowledgeDoc } from "../../lib/demo/demoData";
import styles from "./KnowledgePage.module.css";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  useEffect(() => {
    void listDocuments().then(setDocs);
  }, []);

  return (
    <>
      <Header />
      <main className="container">
        <p className="eyebrow">Base de conhecimento</p>
        <h1 className={styles.title}>Documentos que alimentam o oráculo</h1>
        <div style={{ margin: "16px 0" }}><Badge tone="emerald">Sincronizado com o Notion</Badge></div>
        <p className={styles.note}>
          Somente leitura. Lista dos documentos aprovados atualmente indexados. É daqui
          — e só daqui — que o oráculo tira as respostas.
        </p>
        <table className={styles.table}>
          <thead>
            <tr><th>Documento</th><th>Sincronização</th><th>Status</th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <div className={styles.docCell}>
                    <SourceTypeTag kind={d.kind} />
                    <div>
                      <strong>{d.title}</strong>
                      <span className={styles.origin}>{d.origin}{d.version ? ` · ${d.version}` : " · —"}</span>
                    </div>
                  </div>
                </td>
                <td className={styles.mono}>{d.syncedAt}</td>
                <td>
                  <span className={d.status === "active" ? styles.active : styles.syncing}>
                    ● {d.status === "active" ? "Ativo" : "Sincronizando"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className={styles.footnote}>
          🔒 Documentos 🔴 <strong>Restrito</strong> e materiais confidenciais não são indexados e nunca chegam ao oráculo.
        </div>
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 3: Implement `KnowledgePage.module.css`**

```css
.title { font-size: clamp(2.2rem, 5vw, 3.4rem); margin: var(--space-4) 0; }
.note { color: var(--text-muted); max-width: 60ch; }
.table { width: 100%; border-collapse: collapse; margin-top: var(--space-6); }
.table th { text-align: left; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; color: var(--text-muted); padding: 12px 8px; border-bottom: 1px solid var(--border); }
.table td { padding: 18px 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.docCell { display: flex; align-items: center; gap: 14px; }
.docCell strong { display: block; }
.origin { color: var(--text-muted); font-size: .82rem; }
.mono { font-family: var(--font-mono); color: var(--text-muted); }
.active { color: var(--emerald); }
.syncing { color: #f0b429; }
.footnote { margin: var(--space-6) 0; padding: var(--space-4); border-radius: var(--radius); background: var(--surface-1); border: 1px solid var(--border); color: var(--text-muted); }
@media (max-width: 720px) { .origin { display: none; } }
```

- [ ] **Step 4: Wire the route and commit**

In `App.tsx`:
```tsx
import KnowledgePage from "./features/knowledge/KnowledgePage";
// ...
<Route path="/knowledge" element={<KnowledgePage />} />
```
Run: `cd frontend && npx tsc -b && npm run dev` → open `/knowledge`, compare to screenshots.
```bash
git add frontend/src/features/knowledge frontend/src/data/documents.ts frontend/src/App.tsx
git commit -m "feat(frontend): add knowledge base page"
```

---

### Task 9: Oracle chat app

**Files:**
- Create: `frontend/src/features/chat/ChatPage.tsx`, `ChatPage.module.css`
- Create: `frontend/src/features/chat/components/Sidebar.tsx`
- Create: `frontend/src/features/chat/components/MessageList.tsx`
- Create: `frontend/src/features/chat/components/MessageBubble.tsx`
- Create: `frontend/src/features/chat/components/CitationsBlock.tsx`
- Create: `frontend/src/features/chat/components/CitationCard.tsx`
- Create: `frontend/src/features/chat/components/Composer.tsx`
- Create: `frontend/src/features/chat/components/EmptyState.tsx`
- Create: `frontend/src/features/chat/components/ThinkingIndicator.tsx`
- Create: `frontend/src/features/chat/components/ErrorState.tsx`
- Modify: `frontend/src/App.tsx` (wire `/oracle` and `/oracle/:conversationId`)

**Interfaces:**
- Consumes: `useConversations`, `useConversation`, `useAskStream`; `Logo`, `SourceTypeTag`; `safeUrl`; types from Task 2; `useNavigate`, `useParams` from react-router.
- Produces: `<ChatPage />`; local turn model `Turn = { role: "user" | "assistant"; content: string; citations?: Citation[] }`.

Screenshot reference: dark two-pane layout. Left sidebar: Logo + "Oracle Borderless", "+ Nova conversa" gradient button, "CONVERSAS" list with relative dates, footer links "Sobre & Fontes"/"Base de conhecimento" and a user chip "duanne@mail.com · autenticado na borda". Main: top bar "Nova conversa" + green "Respondendo só com fontes aprovadas do Notion", user email chip top-right. Empty state: big logo, "Olá! Pergunte qualquer coisa.", subcopy, 4 example chips (GROWTH/CULTURA/OPERAÇÃO/DEMO — the DEMO one is "Ver o estado de erro (falha ao gerar)"). Active conversation: user bubble (violet, right), assistant answer, "N FONTES CITADAS" block with expandable cards `[n]`. Composer fixed bottom "Faça sua pergunta..." with send arrow; footnote "O oráculo responde só com fontes aprovadas · nada confidencial".

- [ ] **Step 1: Implement `CitationCard.tsx` and `CitationsBlock.tsx`**

`CitationCard.tsx`:
```tsx
import { useState } from "react";
import type { Citation } from "../../../lib/types";
import { SourceTypeTag } from "../../../components/SourceTypeTag/SourceTypeTag";
import { safeUrl } from "../../../lib/utils/safeUrl";
import styles from "../ChatPage.module.css";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [open, setOpen] = useState(false);
  const href = safeUrl(citation.url);
  return (
    <div className={styles.citation}>
      <button className={styles.citationHead} onClick={() => setOpen((o) => !o)}>
        <SourceTypeTag kind={citation.source_type} />
        <strong>{citation.title}</strong>
        <span className={styles.citationIndex}>[{index}] ▾</span>
      </button>
      {open && (
        <div className={styles.citationBody}>
          <p>{citation.snippet}</p>
          {href && <a href={href} target="_blank" rel="noreferrer">Abrir no Notion →</a>}
        </div>
      )}
    </div>
  );
}
```
`CitationsBlock.tsx`:
```tsx
import type { Citation } from "../../../lib/types";
import { CitationCard } from "./CitationCard";
import styles from "../ChatPage.module.css";

export function CitationsBlock({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className={styles.citations}>
      <div className={styles.citationsLabel}>◆ {citations.length} fontes citadas</div>
      {citations.map((c, i) => (
        <CitationCard key={`${c.title}-${i}`} citation={c} index={i + 1} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Implement `MessageBubble.tsx`, `MessageList.tsx`, `ThinkingIndicator.tsx`, `ErrorState.tsx`**

`MessageBubble.tsx`:
```tsx
import type { Citation } from "../../../lib/types";
import { Logo } from "../../../components/Logo/Logo";
import { CitationsBlock } from "./CitationsBlock";
import styles from "../ChatPage.module.css";

type Props = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
};

export function MessageBubble({ role, content, citations, streaming }: Props) {
  if (role === "user") {
    return <div className={styles.userTurn}><div className={styles.userBubble}>{content}</div></div>;
  }
  return (
    <div className={styles.botTurn}>
      <Logo size={34} />
      <div className={styles.botBody}>
        <div className={styles.botText}>
          {content}
          {streaming && <span className={styles.cursor} />}
        </div>
        {citations && <CitationsBlock citations={citations} />}
      </div>
    </div>
  );
}
```
`MessageList.tsx`:
```tsx
import type { Citation } from "../../../lib/types";
import { MessageBubble } from "./MessageBubble";

export type Turn = { role: "user" | "assistant"; content: string; citations?: Citation[] };

export function MessageList({ turns, streamingIndex }: { turns: Turn[]; streamingIndex: number | null }) {
  return (
    <>
      {turns.map((t, i) => (
        <MessageBubble
          key={i}
          role={t.role}
          content={t.content}
          citations={t.citations}
          streaming={streamingIndex === i}
        />
      ))}
    </>
  );
}
```
`ThinkingIndicator.tsx`:
```tsx
import { Logo } from "../../../components/Logo/Logo";
import styles from "../ChatPage.module.css";

export function ThinkingIndicator() {
  return (
    <div className={styles.botTurn}>
      <Logo size={34} />
      <div className={styles.thinking}><span /><span /><span /></div>
    </div>
  );
}
```
`ErrorState.tsx`:
```tsx
import styles from "../ChatPage.module.css";

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className={styles.errorBox}>
      <p>{message}</p>
      <button className={styles.retry} onClick={onRetry}>Tentar novamente</button>
    </div>
  );
}
```

- [ ] **Step 3: Implement `Composer.tsx`, `EmptyState.tsx`, `Sidebar.tsx`**

`Composer.tsx`:
```tsx
import { useState } from "react";
import styles from "../ChatPage.module.css";

export function Composer({ onSend, disabled }: { onSend: (q: string) => void; disabled?: boolean }) {
  const [value, setValue] = useState("");
  function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (!q || disabled) return;
    onSend(q);
    setValue("");
  }
  return (
    <form className={styles.composer} onSubmit={submit}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Faça sua pergunta..."
      />
      <button type="submit" aria-label="Enviar" disabled={disabled}>↑</button>
    </form>
  );
}
```
`EmptyState.tsx`:
```tsx
import { Logo } from "../../../components/Logo/Logo";
import styles from "../ChatPage.module.css";

const EXAMPLES = [
  { tag: "GROWTH", text: "Qual a nomenclatura de campanhas no Meta Ads?" },
  { tag: "CULTURA", text: "Como funciona a Review Mensal (1:1)?" },
  { tag: "OPERAÇÃO", text: "Como é o upload semanal de vídeo no YouTube?" },
  { tag: "DEMO", text: "Ver o estado de erro (falha ao gerar)", value: "[demo-error]" },
];

export function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className={styles.empty}>
      <Logo size={72} />
      <h2>Olá! Pergunte qualquer coisa.</h2>
      <p>Eu respondo sobre as regras e a operação do ecossistema — sempre com base nos documentos aprovados, e sempre citando as fontes.</p>
      <div className={styles.exampleGrid}>
        {EXAMPLES.map((e) => (
          <button key={e.tag} className={styles.exampleCard} onClick={() => onPick(e.value ?? e.text)}>
            <span className={styles.exampleTag}>{e.tag}</span>
            <span>{e.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```
`Sidebar.tsx`:
```tsx
import { Link } from "react-router-dom";
import { Logo } from "../../../components/Logo/Logo";
import type { ConversationSummary } from "../../../lib/types";
import styles from "../ChatPage.module.css";

type Props = {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onOpen: (id: string) => void;
  userEmail: string;
};

export function Sidebar({ conversations, activeId, onNew, onOpen, userEmail }: Props) {
  return (
    <aside className={styles.sidebar}>
      <Link to="/" className={styles.sidebarBrand}><Logo size={34} /> Oracle Borderless</Link>
      <button className={styles.newBtn} onClick={onNew}>+ Nova conversa</button>
      <div className={styles.listLabel}>Conversas</div>
      <ul className={styles.convList}>
        {conversations.map((c) => (
          <li key={c.id}>
            <button
              className={c.id === activeId ? styles.convActive : styles.convItem}
              onClick={() => onOpen(c.id)}
            >
              <strong>{c.title ?? "(sem título)"}</strong>
            </button>
          </li>
        ))}
      </ul>
      <div className={styles.sidebarFoot}>
        <Link to="/about">Sobre &amp; Fontes</Link>
        <Link to="/knowledge">Base de conhecimento</Link>
        <div className={styles.userChip}>
          <span className={styles.avatar}>{userEmail[0]?.toUpperCase()}</span>
          <div><strong>{userEmail}</strong><span>autenticado na borda</span></div>
        </div>
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Implement `ChatPage.tsx` (orchestration)**

```tsx
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useConversations } from "../../hooks/useConversations";
import { useConversation } from "../../hooks/useConversation";
import { useAskStream } from "../../hooks/useAskStream";
import { Sidebar } from "./components/Sidebar";
import { MessageList, type Turn } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { ThinkingIndicator } from "./components/ThinkingIndicator";
import { ErrorState } from "./components/ErrorState";
import styles from "./ChatPage.module.css";

const USER_EMAIL = "duanne@mail.com"; // demo placeholder; real identity is a fast-follow

export default function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { conversations, refresh } = useConversations();
  const { detail } = useConversation(conversationId);
  const stream = useAskStream();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [lastQuestion, setLastQuestion] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load history when opening an existing conversation.
  useEffect(() => {
    if (detail) setTurns(detail.messages.map((m) => ({ role: m.role, content: m.content, citations: m.sources })));
    else if (!conversationId) setTurns([]);
  }, [detail, conversationId]);

  // Reflect the streaming answer into the last assistant turn.
  useEffect(() => {
    if (stream.status === "idle") return;
    setTurns((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, content: stream.answer, citations: stream.citations.length ? stream.citations : last.citations };
      }
      return next;
    });
  }, [stream.answer, stream.citations, stream.status]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, stream.status]);

  useEffect(() => {
    if (stream.status === "done") void refresh();
  }, [stream.status, refresh]);

  async function send(question: string) {
    setLastQuestion(question);
    setTurns((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "" }]);
    await stream.ask({ question, conversationId });
  }

  function newConversation() {
    setTurns([]);
    stream.reset();
    navigate("/oracle");
  }

  const streamingIndex = stream.status === "streaming" || stream.status === "thinking" ? turns.length - 1 : null;
  const showThinking = stream.status === "thinking";
  const showError = stream.status === "error";

  return (
    <div className={styles.shell}>
      <Sidebar
        conversations={conversations}
        activeId={conversationId ?? null}
        onNew={newConversation}
        onOpen={(id) => navigate(`/oracle/${id}`)}
        userEmail={USER_EMAIL}
      />
      <div className={styles.main}>
        <header className={styles.topbar}>
          <div>
            <strong>{turns.length ? "Conversa" : "Nova conversa"}</strong>
            <span className={styles.topSub}>● Respondendo só com fontes aprovadas do Notion</span>
          </div>
          <span className={styles.emailChip}>{USER_EMAIL}</span>
        </header>
        <div className={styles.thread} ref={scrollRef}>
          {turns.length === 0 && stream.status === "idle" ? (
            <EmptyState onPick={send} />
          ) : (
            <div className={styles.threadInner}>
              <MessageList turns={turns} streamingIndex={showThinking ? null : streamingIndex} />
              {showThinking && <ThinkingIndicator />}
              {showError && <ErrorState message={stream.errorMessage ?? "Erro ao gerar a resposta."} onRetry={() => send(lastQuestion)} />}
            </div>
          )}
        </div>
        <div className={styles.composerWrap}>
          <Composer onSend={send} disabled={stream.status === "thinking" || stream.status === "streaming"} />
          <p className={styles.composerNote}>O oráculo responde só com fontes aprovadas · nada confidencial</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement `ChatPage.module.css`**

```css
.shell { display: grid; grid-template-columns: 300px 1fr; height: 100vh; }
.sidebar { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-4); border-right: 1px solid var(--border); background: var(--surface-1); overflow: hidden; }
.sidebarBrand { display: flex; align-items: center; gap: 10px; font-weight: 800; }
.newBtn { background: var(--gradient); color: #06231b; padding: 12px; border-radius: var(--radius); font-weight: 700; }
.listLabel { font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; color: var(--text-muted); }
.convList { list-style: none; display: grid; gap: 6px; overflow-y: auto; flex: 1; }
.convItem, .convActive { width: 100%; text-align: left; padding: 12px; border-radius: var(--radius-sm); color: var(--text); }
.convItem:hover { background: var(--surface-2); }
.convActive { background: var(--violet-soft); }
.sidebarFoot { display: grid; gap: 10px; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: var(--space-3); }
.userChip { display: flex; align-items: center; gap: 10px; background: var(--surface-2); border-radius: var(--radius); padding: 10px; }
.userChip span:last-child { color: var(--text-muted); font-size: .78rem; display: block; }
.avatar { display: inline-flex; width: 30px; height: 30px; align-items: center; justify-content: center; border-radius: 50%; background: var(--violet); color: #fff; }
.main { display: flex; flex-direction: column; min-width: 0; }
.topbar { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4) var(--space-6); border-bottom: 1px solid var(--border); }
.topSub { display: block; color: var(--emerald); font-size: .82rem; }
.emailChip { background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 8px 14px; font-size: .85rem; }
.thread { flex: 1; overflow-y: auto; padding: var(--space-6); }
.threadInner { max-width: 820px; margin: 0 auto; display: grid; gap: var(--space-5); }
.empty { max-width: 760px; margin: 8vh auto 0; text-align: center; display: grid; justify-items: center; gap: var(--space-4); }
.empty p { color: var(--text-muted); max-width: 48ch; }
.exampleGrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); margin-top: var(--space-4); }
.exampleCard { text-align: left; background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-4); display: grid; gap: 8px; }
.exampleCard:hover { border-color: var(--violet); }
.exampleTag { font-family: var(--font-mono); font-size: .66rem; letter-spacing: .1em; color: #c9b6ff; }
.userTurn { display: flex; justify-content: flex-end; }
.userBubble { background: var(--violet); padding: 14px 18px; border-radius: 16px 16px 4px 16px; max-width: 70%; }
.botTurn { display: flex; gap: 14px; align-items: flex-start; }
.botBody { flex: 1; min-width: 0; }
.botText { white-space: pre-wrap; line-height: 1.6; }
.cursor { display: inline-block; width: 8px; height: 1.1em; margin-left: 2px; background: var(--emerald); vertical-align: text-bottom; animation: blink 1s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.thinking { display: inline-flex; gap: 6px; padding: 10px 0; }
.thinking span { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); animation: bounce 1.2s infinite; }
.thinking span:nth-child(2) { animation-delay: .15s; }
.thinking span:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: .4; } 30% { transform: translateY(-5px); opacity: 1; } }
.citations { margin-top: var(--space-4); display: grid; gap: 10px; }
.citationsLabel { color: var(--text-muted); font-size: .8rem; letter-spacing: .06em; }
.citation { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius); }
.citationHead { display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px; text-align: left; }
.citationIndex { margin-left: auto; font-family: var(--font-mono); color: var(--text-muted); }
.citationBody { padding: 0 14px 14px; color: var(--text-muted); display: grid; gap: 8px; }
.citationBody a { color: var(--emerald); }
.errorBox { background: rgba(240,52,52,.1); border: 1px solid rgba(240,52,52,.4); border-radius: var(--radius); padding: var(--space-4); display: grid; gap: 10px; justify-items: start; }
.retry { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 14px; }
.composerWrap { padding: var(--space-4) var(--space-6) var(--space-5); }
.composer { max-width: 820px; margin: 0 auto; display: flex; align-items: center; gap: 10px; background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 8px 8px 8px 18px; }
.composer input { flex: 1; background: none; border: none; outline: none; padding: 10px 0; }
.composer button { width: 40px; height: 40px; border-radius: 50%; background: var(--surface-2); }
.composer button:disabled { opacity: .4; }
.composerNote { text-align: center; color: var(--text-muted); font-size: .8rem; margin-top: var(--space-3); }
@media (max-width: 820px) {
  .shell { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .exampleGrid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 6: Wire routes in `App.tsx`**

```tsx
import ChatPage from "./features/chat/ChatPage";
// ...
<Route path="/oracle" element={<ChatPage />} />
<Route path="/oracle/:conversationId" element={<ChatPage />} />
```

- [ ] **Step 7: Verify and commit**

Run: `cd frontend && npx tsc -b && npm run dev` → open `/oracle`. Check: empty state with 4 chips; click a normal chip → thinking dots → tokens stream with blinking cursor → citation cards expand; click "Ver o estado de erro" chip → error box with "Tentar novamente"; open a sidebar conversation → history loads.
```bash
git add frontend/src/features/chat frontend/src/App.tsx
git commit -m "feat(frontend): add oracle chat app with streaming and citations"
```

---

### Task 10: Full-suite verification, README, and build

**Files:**
- Create: `frontend/README.md`
- Modify: `.gitignore` (root) if needed to ignore `frontend/node_modules` and `frontend/dist`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Run the whole test suite**

Run: `cd frontend && npm run test`
Expected: all suites pass (sse, safeUrl, demoStream, useAskStream).

- [ ] **Step 2: Type-check and production build**

Run: `cd frontend && npm run build`
Expected: `tsc -b` clean, `vite build` emits `dist/` with no errors.

- [ ] **Step 3: Create `frontend/README.md`**

```markdown
# Oracle Borderless — Frontend

React + TypeScript + Vite SPA for the Oracle Borderless product.

## Scripts
- `npm run dev` — dev server (proxies `/conversations` to `http://localhost:8000`)
- `npm run build` — type-check + production build to `dist/`
- `npm run test` — unit tests (Vitest)

## Environment
Copy `.env.example` to `.env`:
- `VITE_DEMO_MODE=true` — runs fully offline with seeded demo data.
- `VITE_DEMO_MODE=false` + `VITE_API_BASE_URL=` — talks to the FastAPI backend.

## Structure
- `src/lib/` — types, API client, SSE parser, demo data/stream, utils
- `src/data/` — data-source abstraction (api vs demo)
- `src/hooks/` — streaming + data hooks
- `src/components/` — shared UI (Logo, Button, Header, Footer, …)
- `src/features/` — landing, about, knowledge, chat

## Logo
`src/assets/logo.svg` is a faithful recreation. To use the official artwork,
drop it at `src/assets/logo.png` and point `Logo.tsx` at it.

## Auth / user identity
The header email is a demo placeholder. In production the identity comes from
the Cloudflare `cf-access-authenticated-user-email` header at the edge; wiring
a real `getCurrentUser()` endpoint is a fast-follow.
```

- [ ] **Step 4: Ensure root `.gitignore` ignores frontend build artifacts**

Confirm `frontend/node_modules` and `frontend/dist` are ignored (either by root `.gitignore` or `frontend/.gitignore` from Task 1). Add to root `.gitignore` if missing:
```
frontend/node_modules
frontend/dist
```

- [ ] **Step 5: Final commit**

```bash
git add frontend/README.md .gitignore
git commit -m "docs(frontend): add README and finalize build config"
```

---

## Self-Review

**Spec coverage:**
- Landing → Task 6 ✓; About & Sources → Task 7 ✓; Knowledge base → Task 8 ✓; Chat app (sidebar/streaming/citations/states) → Task 9 ✓.
- Real API + demo mode → Tasks 2/3 ✓ (`data/source.ts` switch). SSE-over-POST → Task 2 ✓. Citation URL safety → Task 3 ✓. English identifiers + pt-BR copy → all tasks ✓. Design tokens from logo → Task 5 ✓. Logo as SVG override-able → Tasks 5/10 ✓. User identity fast-follow → Task 9 placeholder + README ✓. Tests (sse/useAskStream/demoStream/safeUrl) → Tasks 2/3/4 ✓.

**Placeholder scan:** No TBD/TODO. `data/documents.ts` intentionally returns demo data in both branches with a documented reason (no real endpoint yet) — not a placeholder gap.

**Type consistency:** `AskEvent`, `Citation`, `ConversationSummary/Detail`, `Turn`, `AskStatus`, and the `data/source.ts` signatures (`listConversations`/`getConversation`/`askStream`) are used consistently across Tasks 2–9. `KnowledgeDoc` defined in Task 3, consumed in Task 8. `safeUrl` defined in Task 3, used in Task 9.

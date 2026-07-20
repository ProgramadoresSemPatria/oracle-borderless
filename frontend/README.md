# Oracle Borderless — Frontend

React + TypeScript + Vite SPA for the Oracle Borderless product.

## Scripts

- `npm run dev` — dev server (proxies `/conversations` to `http://localhost:8000`)
- `npm run build` — type-check + production build to `dist/`
- `npm run test` — unit tests (Vitest)

## Environment

Copy `.env.example` to `.env`:

- `VITE_DEMO_MODE=true` — runs fully offline with seeded demo data.
- `VITE_DEMO_MODE=false` + `VITE_API_BASE_URL=<url>` — talks to the FastAPI backend.

The app detects demo mode via `import.meta.env.VITE_DEMO_MODE === "true"` and routes all API calls through the appropriate data source (see `src/data/source.ts`).

## Structure

- `src/lib/` — types, API client, SSE parser, demo data/stream, utils
- `src/data/` — data-source abstraction (api vs demo)
- `src/hooks/` — streaming + data hooks (`useAskStream`, custom hooks)
- `src/components/` — shared UI (Logo, Button, Header, Footer, Container, …)
- `src/features/` — landing, about, knowledge, chat

## Logo

`src/assets/logo.svg` is a faithful recreation of the oracle concept. To use official artwork, drop it at `src/assets/logo.png` and update `Logo.tsx` to import it instead.

## Tests

11 tests across 4 files (sse, safeUrl, demoStream, useAskStream). Run `npm run test` or `npm run test:watch` for watch mode.

## Auth / user identity

The header email is a demo placeholder (`duanne@oracle.local`). In production, user identity comes from the Cloudflare `cf-access-authenticated-user-email` header at the edge. Wiring a real `getCurrentUser()` endpoint backend is a fast-follow.

## Development

```bash
# Install dependencies
npm install

# Start dev server (runs on http://localhost:5173, proxies /conversations to localhost:8000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Watch mode for tests
npm run test:watch
```

All code is English-identified (function/variable names, type definitions), with user-facing copy in Portuguese (pt-BR) via `src/i18n/` or inline JSX.

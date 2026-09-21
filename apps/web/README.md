# Jev Triage Board (web)

TanStack Start front-end for the board. See the root `README.md` for the whole
picture and `../api/README.md` for the backend.

## Run

```bash
pnpm install          # at the repo root
pnpm dev              # http://localhost:3000, expects the API on :8000
```

`API_URL` (default `http://localhost:8000`) is read server-side only; copy
`.env.example` to `.env` to change it.

## Structure

```
src/
  router.tsx               Router plus QueryClient (SSR query integration)
  routes/__root.tsx        Document shell and toaster
  routes/index.tsx         Board route; loader prefetches tickets and meta
  server/env.ts            Server-only env
  server/api-client.ts     Generated client config and error unwrapping
  server/tickets.ts        Server functions: fetch, add, move, retriage, patch, remove
  lib/api/generated/       Client generated from ../api/openapi.json
  lib/queries.ts           Query options and mutation hooks (optimistic move, toasts)
  lib/board.ts             Columns, labels, badge classes, grouping
  lib/fixtures.ts          Test fixtures
  components/              Board, column, card, detail panel, dialogs, banner
  components/ui/           shadcn/ui components
```

## Commands

```bash
pnpm test              # vitest, API mocked
pnpm lint              # eslint
pnpm typecheck         # tsc, run after build or dev so routeTree.gen.ts exists
pnpm build             # vite build, server output in .output/
pnpm start             # node .output/server/index.mjs
pnpm generate:client   # regenerate src/lib/api/generated from ../api/openapi.json
```

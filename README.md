# Jev Triage Board

A Kanban board for support tickets where TypeSafe AI's **Jev** decides the
department, the urgency and whether a refund is being requested. Move a card
into the Triaged column and the answers appear as badges, with the full
probability breakdown one click away.

Monorepo with two apps:

| App        | Stack                                                          | Port |
| ---------- | -------------------------------------------------------------- | ---- |
| `apps/web` | TanStack Start, React 19, TanStack Query, Tailwind 4, shadcn/ui | 3000 |
| `apps/api` | FastAPI, SQLModel on SQLite, httpx, Python 3.13 via uv          | 8000 |

The browser never talks to FastAPI directly. TanStack Query calls Start server
functions, which call a client generated from the API's OpenAPI document.

## Quick start

Requirements: Node 20+, pnpm, [uv](https://docs.astral.sh/uv/). No AI key
needed: without one the API runs a deterministic mock triage and the board says
so in a banner.

```bash
./run.sh
```

It installs whatever is missing and starts both apps. `./run.sh --check` runs
the tests, linters, typecheck and build instead. By hand, the same is:

```bash
pnpm install
uv sync --directory apps/api
pnpm dev
```

Open http://localhost:3000. The API seeds ten sample tickets across all four
columns on first start.

To use the real model, copy `apps/api/.env.example` to `apps/api/.env` and set
either `TYPESAFE_API_KEY` (a TypeSafe AI account, calls Jev directly) or
`AI_GATEWAY_API_KEY` (Vercel AI Gateway). The provider switches automatically,
preferring TypeSafe when both are set. See `apps/api/README.md` for every
variable.

## How it works

- **Columns** are workflow status: New, Triaged, In progress, Done. Cards move
  freely between them by drag and drop.
- **Triage runs** when a card enters Triaged without an active result. The API
  asks three typed questions about the ticket: a department choice, a
  five-level urgency score and a refund boolean. If the provider fails, the
  move is rejected and the card snaps back with a toast.
- **Moving a card back to New discards its triage.** The result and any human
  override go to a history table and the card reads "Not triaged, 1 discarded".
  Re-triage archives the result it replaces the same way. Discarded results
  are never consulted again; the detail panel lists them collapsed under
  "Previous triages".
- **Card badges** show the effective department, urgency level out of five and
  a Refund tag. A `*` marks a department overridden by a person.
- **Detail panel** (click a card) shows the description, the probability
  distribution for every question, the provider's confidence, which provider
  answered, a department select that stores a human override next to Jev's
  suggestion, and Re-triage and Delete buttons.
- **Providers.** `typesafe` calls Jev at TypeSafe's own endpoint, `jev` calls
  it through Vercel AI Gateway, and `mock` uses keyword heuristics with
  synthesized probabilities so the board behaves the same without a key. Every
  result records which provider answered.

## Commands

Root scripts run both apps.

```bash
pnpm dev             # both dev servers
pnpm test            # pytest then vitest
pnpm lint            # ruff then eslint
pnpm export:openapi  # apps/api/openapi.json from the FastAPI app
pnpm generate:client # apps/web/src/lib/api/generated from openapi.json
```

Change a route or schema in the API, then run the last two in that order.

## Layout

```
apps/
  api/                 FastAPI app; see apps/api/README.md
    app/triage/        Triage port, Jev and mock adapters, mapping service
    app/routers/       /tickets and /meta
    tests/             pytest, runs against the mock provider
    openapi.json       Exported contract consumed by the web app
  web/                 TanStack Start app; see apps/web/README.md
    src/server/        Server functions wrapping the generated client
    src/lib/           Queries, board helpers, generated client
    src/components/    Board, column, card, detail panel, dialogs
    src/routes/        File-based routes
CLAUDE.md              Design decisions and conventions for this repo
TODO.md                Deferred work
```

## History

The first version of this repo was a NestJS CLI that triaged the same tickets
through the AI SDK's `experimental_evaluate`. It lives in git history at
commit `5c3de9f`.

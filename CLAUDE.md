# CLAUDE.md

Project guidance for the Jev triage board monorepo. The global
`~/.claude/CLAUDE.md` targets a Vue front-end and does not apply here beyond
its critical rules (no em-dash character U+2014, no generated-by lines, answer
questions without changing code, the user commits manually).

## Read first

`README.md` describes how the app works and what Jev is asked.
`docs/context.md` holds every decision with its reason, provider wire
formats, alternatives rejected, verified state and operational gotchas. Read
both before changing scope or providers. Past states live in git; docs
describe the current app only.

## What this is

A Kanban board (`apps/web`, TanStack Start) backed by a FastAPI service
(`apps/api`) that triages support tickets with TypeSafe AI's Jev. Usage is in
`README.md` and the per-app READMEs. This file records decisions and rules.

## Decisions (interview on 2026-09-21)

- Columns are workflow status (New, Triaged, In progress, Done), not
  departments. Department, urgency and refund are badges on the card.
- Triage runs when a card first enters Triaged. Auto-triage on create and
  realtime updates are deferred in `TODO.md`.
- A failed triage rejects the move (HTTP 502 from the API, optimistic update
  rolled back in the UI, toast shown). A card in Triaged always has a result.
- Moving a card into New discards the active triage: the result and the
  human override are copied to `TriageRecord` (reason `moved_to_new`) and
  cleared on the ticket, so re-entering Triaged runs triage again. Re-triage
  archives the replaced result with reason `retriaged`. History is returned
  on every ticket as `history`, newest first, and is display-only: nothing
  reads it for decisions. The detail panel shows it collapsed.
- Department override is a human decision stored beside Jev's suggestion.
  `effective_department` is override if set, else Jev's choice.
- Ten seed tickets span all columns. Results outside New are static fixtures
  with `"provider": "seed"`, so the board works without any provider call.
- Providers: `TRIAGE_PROVIDER=auto` picks `typesafe` when `TYPESAFE_API_KEY`
  is set, else `jev` when `AI_GATEWAY_API_KEY` is set, else `mock`. `mock` is
  deterministic keyword heuristics with synthesized probabilities. The board
  shows a banner whenever `/meta` reports the mock. Every stored result
  records its provider.
- Python calls Jev over plain HTTP, no TypeSafe or Vercel SDK. `typesafe.py`
  posts to `POST {TYPESAFE_BASE_URL}/systemone` in TypeSafe's wire format
  (yes/no questions are type `noul`, answers carry `noul` or per-answer
  `confidence`, score probabilities are keyed by 0-based index strings).
  `jev.py` posts to the gateway's `/v1/evaluate` with the AI SDK naming
  (`boolean`, `probability`, confidence under `providerMetadata`). Both map
  to the same `TriageEvaluation`.
- Emerson keeps `TYPESAFE_API_KEY` in `apps/api/.env`. Never read or print
  that file. Verify live behavior through the running API's responses only.
- The web app never calls FastAPI from the browser. Server functions in
  `apps/web/src/server/tickets.ts` wrap the generated client; TanStack Query
  calls the server functions; route loaders prefetch through the QueryClient.

## API rules (`apps/api`)

- Ports and adapters. `app/triage/port.py` is the contract; `jev.py` and
  `mock.py` implement it; `service.py` maps an evaluation to the stored
  `TriageResult` (1-based urgency level as argmax, 1-based mean, refund at
  `REFUND_THRESHOLD` 0.5, provider name, timestamp). `factory.py` picks the
  adapter from settings at startup and stores it on `app.state`.
- Routers stay thin. Triage side effects live in `run_triage` in
  `routers/tickets.py`, which converts `TriageError` to HTTP 502.
- `operation_id` in `main.py` uses the route name so generated client
  functions read `listTickets`, `moveTicket`. Keep route function names stable.
- Tests use the mock provider and an in-memory SQLite engine through
  `dependency_overrides`. Never hit the network in tests; `respx` records the
  gateway for `test_jev_provider.py`.
- After changing routes or schemas: `pnpm export:openapi` then
  `pnpm generate:client`. Commit `openapi.json` and the generated folder.
- Ruff with `E, F, I, UP, B, SIM`, line length 100, Python 3.13 pinned in
  `.python-version`.

## Web rules (`apps/web`)

- TanStack Start with Vite 8 and nitro for the production server. Router and
  Query are wired by `setupRouterSsrQueryIntegration` in `src/router.tsx`.
- Server functions use `createServerFn().validator(...)` (`inputValidator` is
  deprecated in the installed version). Errors thrown in a handler reach the
  client with their message; `src/server/api-client.ts` turns FastAPI's
  `detail` into that message.
- `src/lib/queries.ts` owns query options and mutation hooks, including the
  optimistic move with rollback and every toast. Components do not call server
  functions directly.
- `src/lib/board.ts` holds column definitions, labels and badge classes. Do not
  duplicate status or department strings in components.
- Drag and drop is `@atlaskit/pragmatic-drag-and-drop`: cards are draggables,
  columns are drop targets, the board has the monitor that calls the move
  mutation. Adapters attach in `useEffect` and return their cleanup.
- shadcn/ui v4 with the radix-nova style. The department select is the shadcn
  `NativeSelect` so it works in jsdom tests and needs no pointer polyfills.
- Tests: Vitest with jsdom and Testing Library, `*.test.ts(x)` beside
  sources. `vi.mock('@/server/tickets')` stands in for the API. Fixtures live
  in `src/lib/fixtures.ts`.
- `src/routeTree.gen.ts` is generated and gitignored; run `pnpm build` or
  `pnpm dev` before `pnpm typecheck` on a fresh clone.
- Chrome automation cannot exercise the drag: synthetic mouse events do not
  produce HTML5 drag events. Dispatching `DragEvent`s with a `DataTransfer`
  does work for manual verification.
- Stopping dev servers: `fastapi dev` runs a reloader whose children have
  `multiprocessing` command lines, so a `pkill` on the fastapi pattern leaves
  them bound to 8000. Kill `jev-ticket-classifier/apps/api/.venv/bin/python` processes too,
  then confirm both ports bind with a socket test before starting again. A
  leftover server with its SQLite file deleted answers reads and returns 500
  on writes, which looks like an application bug.

## Workflow

- Tests first for both apps. Before calling work done, at the root:
  `pnpm test`, `pnpm lint`, and in `apps/web` `pnpm typecheck` and
  `pnpm build`, then `docker compose build` to prove the images still build.
- `run.sh` is Docker only, by Emerson's decision: it must never install or
  start anything on the host. Local dev servers are `pnpm dev` for people
  working on the code, not a supported way to run the app.
- The user commits manually. Do not commit unless told to.
- The `typesafe` provider was verified live on 2026-09-21 (three tickets,
  sub-second responses). The `jev` gateway provider is covered by recorded
  responses only.

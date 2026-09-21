# Project context

Everything a new engineer or agent needs that is not obvious from the code.
`CLAUDE.md` holds the rules; this file holds the decisions, the facts and the
reasoning behind the current state. Past states live in git.

## What this is

A Kanban board for support tickets where TypeSafe AI's Jev decides the
department, the urgency and whether a refund is requested. Jev is a
"System One" evaluation model: it takes typed questions against a piece of
state and returns calibrated probability distributions, not text. The board
makes those decisions visible as badges and, in the detail panel, as
probability bars with per-question confidence.

Owner: Emerson Demetrio. Repo: github.com/emerson-buoy/jev-ticket-classifier.

## History

Git history is the record. The short version: a CLI from a written
spec, rescoped the same day to this board, then triage history, the direct
TypeSafe provider, Docker, and a harm-aware urgency rubric. This document
describes the current state only.

## Decisions and why

Every decision below came from an explicit interview round with Emerson. If
you want to change one, it is a product decision, not a refactor.

| Decision | Chosen | Why |
| --- | --- | --- |
| Column axis | Workflow status: New, Triaged, In progress, Done | Emerson chose status over department columns; department, urgency and refund are badges |
| Framework | TanStack Start (not a Vite SPA) | He wanted the full TanStack experience; server functions are the only client of the API |
| Data path | Browser to TanStack Query to Start server functions to generated OpenAPI client to FastAPI | Keeps the API URL server-side, no CORS |
| Monorepo tooling | pnpm workspaces plus uv, root scripts with concurrently, no Turborepo or Nx | Two apps in two languages gain little from a task graph |
| Persistence | SQLite through SQLModel | Zero infrastructure, survives restarts |
| Triage trigger | On first move into Triaged; auto-triage on create deferred | Emerson: "when I move to triage for now; then automatic" |
| Triage failure | Move rejected, card snaps back, toast; 503 with Retry-After for transient provider failures, 502 otherwise | A card in Triaged always has a result, and the UI can tell "retry" from "bug" |
| Move back to New | Triage discarded into history, override cleared | Emerson asked for discard with historical data kept and shown collapsed |
| Re-triage | Archives the replaced result, clears override; from New the card moves to Triaged, later columns stay | Keeps history complete; Emerson on 2026-09-21: cards triaged from the panel "today they dont" move, and New must never hold a result |
| Seeds | Ten tickets across all columns, static fixture results marked `provider: seed` | Works with no provider, same fixtures serve tests |
| Override | Human department override stored beside Jev's suggestion; `effective_department` = override or suggestion | Shows disagreement, which is useful demo material |
| Detail panel | Description, probability bars, confidence, provider, override select, re-triage, delete, collapsed history | Where the probabilities become visible |
| Mock mode | Automatic when no key, deterministic keyword heuristics, banner on the board, provider recorded on each result | Emerson had no key at first and wanted zero-config runs |
| Python route to Jev | Plain httpx, no TypeSafe or Vercel SDK | Fewest dependencies; both endpoints are plain JSON |
| API contract | Client generated from FastAPI's OpenAPI with `@hey-api/openapi-ts` | One source of truth in the Pydantic models |
| Env layout | Each app owns its `.env` and `.env.example`; API also reads a repo-root `.env` | Emerson: "each app has its own" |
| Tests | pytest with the mock adapter; Vitest plus Testing Library with server functions mocked; no Playwright | Nothing hits the network |
| Realtime | REST for writes plus server-sent events for change notices (`GET /events`, proxied by a Start server route at `/api/events`); WebSockets rejected for now | Emerson, 2026-09-21: the POC is about Jev classification, so the write path stays as is and only server-to-browser notification is added. Revisit WebSockets only if presence, live cursors or collaborative editing become features |
| Urgency rubric | Time pressure and harm weighed together; wrong charges and data loss reach level 4 | A "$500 wrongly debited" ticket scored 2/5 under the original time-pressure-only rubric; Emerson chose to fold harm in rather than add a fourth question |

He prefers framework conventions over bespoke setup for POCs ("this is a
POC anyway").

## Providers and wire formats

All three implement `apps/api/app/triage/port.py` and map to the same
`TriageEvaluation`. Selection is in `factory.py`: `TRIAGE_PROVIDER=auto`
picks `typesafe` with `TYPESAFE_API_KEY`, else `jev` with
`AI_GATEWAY_API_KEY`, else `mock`.

**typesafe** (verified live 2026-09-21)
- `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer`.
- Body: `{model: "jev-latest", state, questions}`. Yes/no questions are type
  `noul`; `choice` criteria is a map of option to description; `score`
  criteria is an ordered array of 2 to 10 level descriptions.
- Answers: choice `{choice, probabilities, confidence}`; score
  `{score, legend, probabilities, confidence}` with probabilities keyed by
  0-based index strings and score a fractional 0-based position; noul
  `{noul}` as P(true). Usage `{input_tokens, output_tokens}`.
- Errors: 401, 422, 429, 529. Observed latency 0.3 to 0.7 s per ticket.
- Live results on the sample tickets were sharp: department at 100%, refund
  at 99% for the double charge, urgency 5/5 for the outage.

**jev** (gateway, tests only)
- `POST https://ai-gateway.vercel.sh/v1/evaluate`, `Authorization: Bearer`.
- Body: `{model: "typesafe-ai/jev", state, questions}` with AI SDK naming:
  `boolean`, `choice`, `score`.
- Answers: choice `{choice, probabilities?}`; score `{score, probabilities?}`
  keyed by 0-based index; boolean `{probability}`. Confidence, when present,
  at `providerMetadata.typesafe.confidence`.
- The gateway requires a Vercel team with a card on file. The AI SDK
  (`ai` 7.0.107) types exactly one evaluation id, `typesafe-ai/jev`; its docs
  also use `typesafe-ai/jev-latest`. Both are accepted.

**mock**
- Keyword heuristics in `mock.py`. Billing words, technical words, general
  words; urgency from critical, pressing, moderate and relaxed phrases;
  refund 0.92 when "refund" appears, 0.25 when negated ("not a refund"),
  0.05 otherwise. Probabilities are synthesized around the chosen answer.

**Urgency rubric** (`questions.py`, changed 2026-09-21 after the live run):
levels 1 to 5 describe time pressure and harm together. Level 3 includes a
small billing error, level 4 includes losing money, being charged for
something not owed, or losing data, level 5 includes significant ongoing
financial or data harm. Verified live: "500 usd wrongly debited" went from
2/5 to 4/5 with 87% mass on level 4; outage, low-priority question and
medium bug tickets kept their levels. The mock mirrors this with a
`HARM_WORDS` list, and its outage keyword is "500 error", not "500", so
amounts do not read as HTTP errors.

**Service mapping** (`service.py`): urgency level is the 1-based argmax of
the distribution (rounded score plus one without one); urgency mean is the
raw score plus one; refund flag at `REFUND_THRESHOLD` 0.5; provider name and
timestamp recorded.

## Alternatives evaluated and rejected or deferred

- **Anthropic key.** Claude can answer the same three questions with
  structured outputs, but returns a decision, not a calibrated distribution.
  Feasible as a fourth adapter; not built. Emerson asked why the app was
  "built around Vercel": it is built around Jev, which was only reachable
  through the gateway until his TypeSafe account came into play.
- **Running Jev locally.** Not possible. Jev is hosted only, no public
  weights, no self-host option. Nearest stand-in is "Jeff"
  (github.com/logan-markewich/jeff), an MIT server speaking the same
  `/v1/systemone` contract on a 400M parameter GLiFormer, noticeably less
  accurate. Would need its own adapter since it speaks the TypeSafe format.
- **Official `typesafe-sdk`** (PyPI 0.7.0) and **Vercel's Python `ai`**
  package (0.7.0, beta). Both work; plain httpx was chosen. Beware
  `typesafe-ai` and `typesafe` on PyPI, which are unaffiliated packages.

## Verified state

| Check | Status |
| --- | --- |
| API pytest | 79 pass, no network |
| Web vitest | 19 pass, API mocked |
| Ruff, ESLint, tsc, build | clean, via `pnpm lint`, `pnpm --filter web typecheck`, `pnpm --filter web build` |
| Browser | board, drag into Triaged, detail panel, override, history verified in Chrome |
| Live Jev | typesafe provider, three tickets |
| Gateway provider | recorded responses only |

## Operational gotchas

- `TYPESAFE_API_KEY` lives in `apps/api/.env`. Never read or print that file.
  Confirm behavior through `GET /meta` and the API's responses only.
- `fastapi dev` runs a reloader whose children have `multiprocessing`
  command lines. Killing the parent pattern leaves them bound to port 8000.
  Kill `jev-ticket-classifier/apps/api/.venv/bin/python` processes and
  bind-test both ports before restarting. A leftover server whose SQLite
  file was deleted answers reads and returns 500 on writes, which looks like
  an application bug. This bit three times in one day.
- Chrome automation cannot perform an HTML5 drag; dispatch `DragEvent`s with
  a `DataTransfer` on the card and the column section instead. Native drags
  by hand work.
- `src/routeTree.gen.ts` is generated and gitignored; run `pnpm build` or
  `pnpm dev` before `pnpm typecheck` on a fresh clone.
- After changing an API route or schema: `pnpm export:openapi` then
  `pnpm generate:client`. Commit both outputs.
- Score answers are 0-based on the wire and 1-based everywhere the UI shows
  them.
- Renaming or moving the repo folder breaks `apps/api/.venv`: uv's console
  scripts keep the old absolute path in their shebang, so `pytest` fails to
  spawn while `python` still works. Fix: `rm -rf apps/api/.venv && uv sync
  --directory apps/api`.

## Docker

`run.sh` is Docker only. Emerson's words: "default AND ONLY action in run is
to run this whole thing AND its deps into docker", "no local support". It
checks Docker is installed and running, warns when no key is configured, and
execs `docker compose up --build`. It no longer installs pnpm, uv or
dependencies on the host; those are for people editing the code (`pnpm dev`).

`docker-compose.yml` runs `api` (Dockerfile in `apps/api`, uv image,
`fastapi run`, healthcheck on `/meta`, SQLite on the `api-data` volume) and
`web` (Dockerfile in `apps/web` built from the repo root because it needs the
workspace lockfile and `apps/api/openapi.json`; nitro server output only).
`web` waits for `api` to be healthy and reaches it at `http://api:8000`.
Verified 2026-09-21: build, health, SSR of the board, a live TypeSafe triage
through the containers, data surviving `restart`.

The web build pins pnpm 11.1.0 via `packageManager` and corepack. Newer pnpm
11.x enforces a one-day minimum release age on lockfile entries, and a
same-day TanStack Query release made the build fail before the pin.

HTTP for both Jev adapters goes through one `HttpEvaluator`
(`app/triage/http.py`): one endpoint, auth set once on the `httpx.Client`,
transport and HTTP errors mapped to `TriageError`, closed on app shutdown.
Adapters only build the payload and parse the answers. Do not pass
`headers=` per call.

Failures are typed (`ProviderUnavailable`, `ProviderRejected`,
`MalformedResponse`). The evaluator retries only `ProviderUnavailable`, with
jittered backoff under `TRIAGE_DEADLINE_SECONDS`. `TriageService` wraps every
call in a `CircuitBreaker` on `app.state`: after
`TRIAGE_CIRCUIT_FAILURES` consecutive unavailable answers the circuit opens
for `TRIAGE_CIRCUIT_COOLDOWN_SECONDS`, calls fail fast with 503 and
`Retry-After`, then one probe is let through. `GET /meta` reports `circuit`
and the board shows a red banner while it is open.

## Live updates

`app/events.py` is an in-process broadcaster: one bounded asyncio queue per
subscriber, publish from the threadpool through `call_soon_threadsafe`, a
subscriber whose queue is full is dropped rather than blocking the writer.
`GET /events` yields `tickets.changed` events with `{id, action}` and an
incrementing id, `retry: 3000` up front, keep-alive comments from FastAPI.
Clients carry no payload state: they refetch on every event and on open, so
reconnects need no replay buffer. Limit: one API process (one uvicorn worker,
one container); a second worker would split subscribers. Replace the
broadcaster with Redis pub/sub or Postgres LISTEN before scaling out.

## Open items

`TODO.md` is the list: what has shipped (PRs 1 to 7, checked), the open
engineering items in suggested order (ticket service extraction, EventSource
reconnect, circuit state over the stream, idempotency keys, optimistic
locking, persistence hygiene, health endpoint, validated settings,
observability, spend budget, comment strip, hook tests, coverage), and the
product decisions that need a yes before anyone builds them: auto-triage on
create, a fallback provider chain, and a live check of the gateway provider
once a Vercel key exists. Package names (`jev-triage-board`,
`jev-triage-api`) and the UI title "Jev Triage Board" predate the repo name
and were left as is.

## Working with Emerson

- He runs scope changes through the `grill-me` interview skill and answers
  rounds in one line per question. Use it for anything that changes scope.
- He wants short factual answers with a recommendation, then he decides.
- He commits manually except when he says "push".
- Never use the em-dash character; never add generated-by lines.

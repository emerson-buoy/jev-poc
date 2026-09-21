# Jev Ticket Classifier POC

A Kanban board for support tickets. Drag a ticket into the Triaged column and
TypeSafe AI's **Jev** decides which department owns it, how urgent it is, and
whether the customer is asking for a refund. Every answer comes with a
probability distribution and a confidence, and you can see all of it on the
card's detail panel.

Jev is a System One model: it does not write text. It evaluates a fixed set of
typed questions against a piece of state and returns calibrated answers. This
POC is about making those answers visible and useful on a board.

## How it works

### The board

Four columns, one per workflow status: **New**, **Triaged**, **In progress**,
**Done**. Cards move freely by drag and drop. **New ticket** in the header
opens a dialog with a title (up to 200 characters) and a description (up to
5000); the ticket lands in New with no classification. The board seeds itself
with ten sample tickets across all four columns on first start.

Each card shows its title, the first lines of the description and, once
triaged, three badges: department, urgency out of five, and a Refund tag when
one is requested. Untriaged cards read "Not triaged" or "Not triaged, N
discarded".

Click a card to open the **detail panel**: the full description, the
probability bars for department and urgency, the refund probability, Jev's
per-question confidence, which provider answered and when, a department
select for a human override, the collapsed list of previous triages, and the
Delete and Triage now / Re-triage buttons.

### What Jev is asked

Every triage sends the ticket's title and description as state, plus these
three questions. The exact text lives in `apps/api/app/triage/questions.py`.

**1. Department** (choice)

> Which team should handle this support ticket?


| Option      | Criteria                                                     |
| ----------- | ------------------------------------------------------------ |
| `billing`   | Payments, invoicing, refunds, billing disputes               |
| `technical` | Bugs, outages, errors, integration or product issues         |
| `general`   | Anything else: account questions, feedback, unclear requests |


**2. Urgency** (score, five ordered levels)

> Rate how urgent this ticket is, weighing time pressure and harm to the
> customer together. Level 1 means no time pressure and no harm. Level 5 means
> an active outage, a customer blocked right now, or significant ongoing
> financial or data harm.


| Level | Criteria                                                                                                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | No time pressure and no harm. Informational, cosmetic, or a question.                                                                                   |
| 2     | Minor inconvenience with an easy workaround. No money or data at stake.                                                                                 |
| 3     | Affecting some of the customer's work, or a small billing error or wrong charge. A workaround exists.                                                   |
| 4     | Blocking part of the customer's work with no good workaround, or the customer is losing money, was charged for something they do not owe, or lost data. |
| 5     | Active outage, the customer is blocked right now, or significant financial or data harm is ongoing.                                                     |


Harm is part of the scale on purpose. A wrong charge blocks nothing, but it
still deserves a fast response. Under a time-pressure-only rubric a "$500
wrongly debited" ticket scored 2/5; under this one it scores 4/5, while
outages, low-priority questions and medium bugs keep their levels.

**3. Refund requested** (yes/no)

> Is the customer explicitly asking for a refund?



### How answers become the classification


| Field on the card | Derived from                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Department        | Jev's chosen option, the one with the highest probability                                                               |
| Urgency `N/5`     | The level with the highest probability. The panel also shows the mean, Jev's probability-weighted position on the scale |
| Refund            | Jev's probability of "yes", flagged when it is 0.5 or above                                                             |
| Confidence        | Jev's per-question confidence, shown in the panel when the provider returns it                                          |
| Provider          | Which backend answered: `typesafe`, `jev` (gateway), `mock` or `seed`                                                   |


The full probability distribution for each question is stored with the
ticket and drawn as bars in the detail panel.

### Rules of the board

- **Triage runs when a card enters Triaged** without an active result. A
  card in Triaged always has a result.
- **A failed triage rejects the move.** The card snaps back and a toast says
  why: "temporarily unavailable, try again" for an outage, rate limit or
  timeout, "provider rejected the request" for a bad key or request, or
  "returned an unusable response" when the answer could not be read.
- **Moving a card back to New discards its triage.** The result and any
  human override go to a history table and are never consulted again. The
  card reads "Not triaged, 1 discarded" and the panel lists past results
  collapsed under "Previous triages". Dragging it into Triaged again asks
  Jev again.
- **Triage from the panel** asks Jev and archives the result it replaces.
  On a card in New it also moves the card to Triaged; cards in later columns
  stay where they are.
- **Override.** The panel's department select stores a human decision next
  to Jev's suggestion. The card shows the human choice with a `*`. Jev's
  original answer stays visible. Re-triage clears the override and keeps it
  on the archived result.
- **Forward moves** between Triaged, In progress and Done never touch the
  result.
- **Delete** removes the ticket and its whole history.
- **Every open browser updates live.** The API pushes a change notice over
  server-sent events after each write, and each board refetches on it and on
  every reconnect. Writes stay plain REST.

### When Jev is slow or down

- **Transient failures are retried.** A timeout, a 429 or a 5xx from the
  provider is retried up to three times with jittered backoff, honouring
  `Retry-After`, inside a 10 second budget per triage. Each attempt has a 3
  second connect and 8 second read timeout, shrunk to whatever budget is
  left. Bad keys and malformed answers are not retried.
- **Sustained failures open a circuit.** After five unavailable answers in a
  row the API stops calling Jev for 30 seconds and rejects moves into
  Triaged immediately with a `Retry-After`. The board shows a red "Jev
  unavailable" banner. After the cooldown one probe call goes through; if it
  succeeds the circuit closes, if not it stays open for another 30 seconds.
- **The provider state is visible.** `GET /meta` reports the active
  provider, whether it is the mock, and the circuit state
  (`closed`, `open`, `half_open`).

### Mock mode

Without an API key the backend runs a deterministic keyword mock that
returns the same shape of answer, with synthesized probabilities, so the
board behaves identically. Department comes from billing, technical and
general word lists, urgency from phrases for critical, pressing, harmful,
moderate and relaxed situations, and refund is 0.92 when "refund" appears,
0.25 when it is negated ("not a refund"), 0.05 otherwise. A banner on the
board says the mock is active, and every result records which provider
produced it. It is a stand-in for demos and tests, not a classifier.

## Running locally

Requirement: Docker with Compose v2. Nothing is installed on your machine.

```bash
./run.sh
```

The script checks that Docker is installed and running, warns when no API
key is configured (mock mode), then runs `docker compose up --build`. The API
is on [http://localhost:8000](http://localhost:8000) with interactive docs at
[http://localhost:8000/docs](http://localhost:8000/docs), the board on
[http://localhost:3000](http://localhost:3000). Ctrl-C stops both. Data lives in the
`api-data` Docker volume and survives restarts; `docker compose down -v`
resets it. `docker compose logs -f api` follows the API log, which is where
provider errors go.

To use the real model, create `apps/api/.env` from `apps/api/.env.example`
and set one of:


| Variable             | Effect                                                       |
| -------------------- | ------------------------------------------------------------ |
| `TYPESAFE_API_KEY`   | Calls Jev directly at TypeSafe. Preferred when both are set. |
| `AI_GATEWAY_API_KEY` | Calls Jev through Vercel AI Gateway.                         |


With neither, the mock runs. Every variable is optional; the API also reads
a repo-root `.env`, and the app-level file wins.


| Variable                          | Default                                    | Meaning                                              |
| --------------------------------- | ------------------------------------------ | ---------------------------------------------------- |
| `TRIAGE_PROVIDER`                 | `auto`                                     | `auto`, `typesafe`, `jev` or `mock`. A forced provider without its key fails at startup |
| `TYPESAFE_BASE_URL`               | `https://api.typesafe.ai/v1`               | TypeSafe API base                                    |
| `TYPESAFE_MODEL_ID`               | `jev-latest`                               | Model id at TypeSafe                                 |
| `AI_GATEWAY_EVALUATE_URL`         | `https://ai-gateway.vercel.sh/v1/evaluate` | Gateway evaluate endpoint                            |
| `JEV_MODEL_ID`                    | `typesafe-ai/jev`                          | Model id at the gateway                              |
| `DATABASE_URL`                    | `sqlite:///./jev.db`                       | SQLModel connection string. Docker sets a path on the volume |
| `TRIAGE_MAX_ATTEMPTS`             | `3`                                        | Provider calls per triage, including retries         |
| `TRIAGE_DEADLINE_SECONDS`         | `10`                                       | Total budget for one triage, all attempts            |
| `TRIAGE_CONNECT_TIMEOUT_SECONDS`  | `3`                                        | Per attempt connect timeout                          |
| `TRIAGE_READ_TIMEOUT_SECONDS`     | `8`                                        | Per attempt read timeout, capped by the budget       |
| `TRIAGE_CIRCUIT_FAILURES`         | `5`                                        | Consecutive unavailable answers that open the circuit |
| `TRIAGE_CIRCUIT_COOLDOWN_SECONDS` | `30`                                       | Seconds the circuit stays open before one probe      |


## Technical details

Two apps in one repository. The browser never talks to the API directly.

```
Browser  ->  TanStack Query  ->  Start server functions  ->  generated client  ->  FastAPI  ->  Jev
Browser  <-  EventSource     <-  Start server route      <-  GET /events       <-  FastAPI
```

### Layout

```
apps/
  api/                       FastAPI app; see apps/api/README.md
    app/main.py              App factory, lifespan (provider, circuit, broadcaster, seed)
    app/config.py            Settings from .env files and the environment
    app/models.py            Ticket and TriageRecord tables
    app/schemas.py           Request and response models
    app/events.py            In-process broadcaster for server-sent events
    app/seed.py              Ten sample tickets
    app/routers/             /tickets, /meta, /events
    app/triage/              Port, adapters, HTTP evaluator, retry policy, circuit, mapping
    tests/                   pytest, mock provider, in-memory SQLite, recorded HTTP
    openapi.json             Exported contract consumed by the web app
  web/                       TanStack Start app; see apps/web/README.md
    src/routes/              index (board) and api/events (stream proxy)
    src/server/              Server functions wrapping the generated client
    src/lib/                 Queries, board helpers, fixtures, generated client
    src/components/          Board, column, card, detail panel, bars, history, dialog, banner
docker-compose.yml           Both services, API volume, healthcheck ordering
run.sh                       Docker-only launcher
.github/workflows/ci.yml     Lint, tests, typecheck, build, Docker build
CLAUDE.md                    Working rules for this repo
docs/context.md              Every decision with its reason, wire formats, gotchas
TODO.md                      Open improvements and pending product decisions
```

### API

FastAPI on Python 3.13, SQLModel on SQLite, httpx, managed with uv.

**Data model.** `Ticket` holds title, description, status, the human
`department_override`, the active triage result as a JSON column, and
timestamps. `TriageRecord` holds discarded results with the override at the
time, a reason (`moved_to_new` or `retriaged`) and when it was discarded.
Every ticket response carries `triage`, `effective_department` (override if
set, else Jev's choice) and `history`, newest first. Tables are created at
startup; there are no migrations.

**Triage pipeline.** A port with three adapters and a chain of guards:

- `app/triage/port.py`: the contract every provider implements, and the
  failure types `ProviderUnavailable`, `ProviderRejected`, `MalformedResponse`.
- `app/triage/typesafe.py`: TypeSafe's `POST /v1/systemone`. Their wire format
  calls the yes/no type `noul` and returns a confidence per answer.
- `app/triage/jev.py`: Vercel AI Gateway's `POST /v1/evaluate`, AI SDK naming.
- `app/triage/mock.py`: keyword heuristics.
- `app/triage/http.py`: the one HTTP path both remote adapters use. Bearer
  auth set once on the client, transport and status errors mapped to the
  failure types (429 and 5xx are unavailable, other 4xx are rejections),
  `RetryPolicy` with jittered exponential backoff under a total deadline,
  per-attempt timeouts bounded by the remaining budget.
- `app/triage/circuit.py`: the circuit breaker, one instance on `app.state`.
- `app/triage/service.py`: wraps every call in the circuit and turns a
  provider's answer into the stored result (argmax level, mean, refund
  threshold, provider, timestamp).
- `app/triage/factory.py`: picks the provider from settings at startup.

**Endpoints.** `GET /meta`, `GET /events`, `GET|POST /tickets`,
`GET|PATCH|DELETE /tickets/{id}`, `POST /tickets/{id}/move`,
`POST /tickets/{id}/triage`. A failed triage answers 503 with `Retry-After`
when the provider is unavailable or the circuit is open, and 502 when it
rejects the request or returns something unusable. The client always gets
one of three fixed messages; the upstream body goes to the log. Routes are
sync and run in the threadpool; the event stream is async.

**Live updates.** `app/events.py` is an in-process broadcaster: one bounded
asyncio queue per subscriber (100 events), thread-safe publish through the
event loop, a subscriber whose queue is full is dropped rather than blocking
a writer. Every router write publishes `tickets.changed` with
`{"id", "action"}` after its commit, where action is `created`, `updated`,
`moved`, `triaged` or `deleted`. A rejected move publishes nothing.
`GET /events` uses FastAPI's built-in `EventSourceResponse`: a `retry: 3000`
hint first, then one event per notification with an incrementing id, keep-
alive comments from the framework, unsubscribe on disconnect. One API
process only; a Redis or Postgres LISTEN broadcaster would replace this
module before running more than one worker.

**Contract.** `apps/api/openapi.json` is exported from the FastAPI app with
`pnpm export:openapi` and committed. The web client under
`apps/web/src/lib/api/generated` is produced from it with
`@hey-api/openapi-ts` (`pnpm generate:client`). It is committed because the
web Docker image has no Python: it copies the JSON and generates the client
during its build. After any route or schema change, run both commands and
commit both outputs. Operation ids are the route function names, so the
generated functions read `listTickets`, `moveTicket`, `streamEvents`.

### Web

TanStack Start with React 19, TanStack Router and Query, Tailwind 4,
shadcn/ui, Atlassian's pragmatic-drag-and-drop. Vite 8 builds it and nitro
serves it.

- `src/server/tickets.ts`: server functions wrapping the generated client;
  `src/server/api-client.ts` turns FastAPI's `detail` into the error message
  the browser sees. `API_URL` is read server-side only.
- `src/lib/queries.ts`: query options and every mutation, including the
  optimistic move with rollback and every toast, plus `useTicketEvents()`,
  which opens an `EventSource` on `/api/events` and invalidates the tickets
  query on every event and on open. Move and re-triage also refetch `/meta`
  so the banner follows the circuit.
- `src/routes/api/events.ts`: a Start server route that fetches the API's
  `/events` with the browser request's abort signal and pipes the body
  through with event-stream headers, so the browser still never reaches
  FastAPI and no CORS is needed.
- `src/routes/index.tsx`: the board route; its loader prefetches tickets and
  meta through the QueryClient so the first render is server-side.
- `src/lib/board.ts`: column definitions, labels, badge classes, grouping.
  Components do not repeat status or department strings.
- Drag and drop: cards are draggables, columns are drop targets, the board
  owns the monitor that calls the move mutation.

### Docker

`apps/api/Dockerfile`: uv image on Python 3.13, dependencies from the lock
file, no dev tools, `fastapi run`, SQLite on the `/data` volume, healthcheck
hitting `/meta` every 10 seconds. `apps/web/Dockerfile`: built from the repo
root because it needs the workspace lock file and `apps/api/openapi.json`,
pnpm 11.1.0 pinned through corepack, generates the client and builds, ships
only the nitro output on `node:22-alpine`. `docker-compose.yml` starts `web`
after `api` is healthy, points it at `http://api:8000`, and reads
`apps/api/.env` into the API when the file exists.

### Tests and CI

`pnpm test` runs pytest then vitest with no network. The API suite (116
tests) uses the mock provider and an in-memory SQLite engine through
dependency overrides, `respx` for recorded TypeSafe and gateway responses,
fake clocks for retries and the circuit, and a recording broadcaster for the
publish points. The event stream generator is tested directly with a fake
request, because the in-process test clients cannot read a few frames of an
endless stream and disconnect. The web suite (26 tests) runs on jsdom with
Testing Library, mocks the server functions, and drives the live-update hook
with a fake `EventSource`.

`.github/workflows/ci.yml` runs `pnpm lint` (Ruff with `E, F, I, UP, B, SIM,
S, RUF, PTH, PT, PERF, RET` and format check, then ESLint), `pnpm test`, the
web build and typecheck, and `docker compose build` on every push to main
and every pull request.

### Developing

Toolchains on the host: Node 20+, pnpm 11.1.0 (corepack), uv.

```bash
pnpm install && uv sync --directory apps/api
pnpm dev             # both dev servers with hot reload, API on :8000, board on :3000
pnpm test            # pytest then vitest, no network
pnpm lint            # ruff then eslint
pnpm export:openapi  # regenerate apps/api/openapi.json after an API change
pnpm generate:client # regenerate the web client from it
```

`src/routeTree.gen.ts` in the web app is generated and gitignored; run
`pnpm build` or `pnpm dev` before `pnpm typecheck` on a fresh clone.
`CLAUDE.md` holds the working rules for this repo, `docs/context.md` the
decisions with their reasons and the operational gotchas, `TODO.md` the open
improvements.

## References

**Jev and TypeSafe AI**

- TypeSafe docs: [https://docs.typesafe.ai/](https://docs.typesafe.ai/)
- HTTP API reference (System One endpoint, request and response shapes): [https://docs.typesafe.ai/api](https://docs.typesafe.ai/api)
- System One concept: [https://docs.typesafe.ai/concepts/system-one](https://docs.typesafe.ai/concepts/system-one)
- Models: [https://docs.typesafe.ai/models](https://docs.typesafe.ai/models)
- Python SDK (not used here, plain HTTP instead): [https://docs.typesafe.ai/sdk/python](https://docs.typesafe.ai/sdk/python)
- Launch coverage: [https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/)

**Vercel AI Gateway route**

- Evaluation modality: [https://vercel.com/docs/ai-gateway/modalities/evaluation](https://vercel.com/docs/ai-gateway/modalities/evaluation)
- TypeSafe-compatible endpoint: [https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe)
- AI SDK `experimental_evaluate` reference: [https://ai-sdk.dev/docs/reference/ai-sdk-core/evaluate](https://ai-sdk.dev/docs/reference/ai-sdk-core/evaluate)

**This app's API**

- Swagger UI when running: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc when running: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Committed OpenAPI document: `apps/api/openapi.json`

**Stack**

- FastAPI: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- FastAPI server-sent events: [https://fastapi.tiangolo.com/tutorial/server-sent-events/](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- SQLModel: [https://sqlmodel.tiangolo.com/](https://sqlmodel.tiangolo.com/)
- uv: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- TanStack Start: [https://tanstack.com/start/latest](https://tanstack.com/start/latest)
- TanStack Start server routes: [https://tanstack.com/start/latest/docs/framework/react/guide/server-routes](https://tanstack.com/start/latest/docs/framework/react/guide/server-routes)
- TanStack Query: [https://tanstack.com/query/latest](https://tanstack.com/query/latest)
- @hey-api/openapi-ts: [https://heyapi.dev/openapi-ts/get-started](https://heyapi.dev/openapi-ts/get-started)
- pragmatic-drag-and-drop: [https://atlassian.design/components/pragmatic-drag-and-drop/about](https://atlassian.design/components/pragmatic-drag-and-drop/about)
- shadcn/ui: [https://ui.shadcn.com/](https://ui.shadcn.com/)
- Tailwind CSS: [https://tailwindcss.com/docs](https://tailwindcss.com/docs)

**Self-hosted stand-in for Jev (not used; Jev has no public weights)**

- Jeff, an MIT server speaking the same System One contract: [https://github.com/logan-markewich/jeff](https://github.com/logan-markewich/jeff)

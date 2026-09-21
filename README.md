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
**Done**. Cards move freely by drag and drop. New tickets arrive in New with
no classification. The board seeds itself with ten sample tickets across all
four columns on first start.

### What Jev is asked

Every triage sends the ticket's title and description as state, plus these
three questions. The exact text lives in `apps/api/app/triage/questions.py`.

**1. Department** (choice)

> Which team should handle this support ticket?

| Option | Criteria |
| --- | --- |
| `billing` | Payments, invoicing, refunds, billing disputes |
| `technical` | Bugs, outages, errors, integration or product issues |
| `general` | Anything else: account questions, feedback, unclear requests |

**2. Urgency** (score, five ordered levels)

> Rate how urgent this ticket is, weighing time pressure and harm to the
> customer together. Level 1 means no time pressure and no harm. Level 5 means
> an active outage, a customer blocked right now, or significant ongoing
> financial or data harm.

| Level | Criteria |
| --- | --- |
| 1 | No time pressure and no harm. Informational, cosmetic, or a question. |
| 2 | Minor inconvenience with an easy workaround. No money or data at stake. |
| 3 | Affecting some of the customer's work, or a small billing error or wrong charge. A workaround exists. |
| 4 | Blocking part of the customer's work with no good workaround, or the customer is losing money, was charged for something they do not owe, or lost data. |
| 5 | Active outage, the customer is blocked right now, or significant financial or data harm is ongoing. |

Harm is part of the scale on purpose. A wrong charge blocks nothing, but it
still deserves a fast response. Under a time-pressure-only rubric a "$500
wrongly debited" ticket scored 2/5; under this one it scores 4/5, while
outages, low-priority questions and medium bugs keep their levels.

**3. Refund requested** (yes/no)

> Is the customer explicitly asking for a refund?

### How answers become the classification

| Field on the card | Derived from |
| --- | --- |
| Department | Jev's chosen option, the one with the highest probability |
| Urgency `N/5` | The level with the highest probability. The panel also shows the mean, Jev's probability-weighted position on the scale |
| Refund | Jev's probability of "yes", flagged when it is 0.5 or above |
| Confidence | Jev's per-question confidence, shown in the panel when the provider returns it |
| Provider | Which backend answered: `typesafe`, `jev` (gateway), `mock` or `seed` |

The full probability distribution for each question is stored with the
ticket and drawn as bars in the detail panel.

### Rules of the board

- **Triage runs when a card enters Triaged** without an active result. If
  the provider fails, the move is rejected, the card snaps back and a toast
  explains why. A card in Triaged always has a result.
- **Moving a card back to New discards its triage.** The result and any
  human override go to a history table and are never consulted again. The
  card reads "Not triaged, 1 discarded" and the panel lists past results
  collapsed under "Previous triages". Dragging it into Triaged again asks
  Jev again.
- **Re-triage** from the panel asks Jev again and archives the result it
  replaces.
- **Override.** The panel's department select stores a human decision next
  to Jev's suggestion. The card shows the human choice with a `*`. Jev's
  original answer stays visible.
- **Forward moves** between Triaged, In progress and Done never touch the
  result.

### Mock mode

Without an API key the backend runs a deterministic keyword mock that
returns the same shape of answer, with synthesized probabilities, so the
board behaves identically. A banner on the board says so, and every result
records which provider produced it. It is a stand-in for demos and tests,
not a classifier.

## Running locally

Requirement: Docker. Nothing is installed on your machine.

```bash
./run.sh
```

This builds both images and starts the API on http://localhost:8000 and the
board on http://localhost:3000. Ctrl-C stops them. Data lives in the
`api-data` Docker volume; `docker compose down -v` resets it.

To use the real model, create `apps/api/.env` from `apps/api/.env.example`
and set one of:

| Variable | Effect |
| --- | --- |
| `TYPESAFE_API_KEY` | Calls Jev directly at TypeSafe. Preferred when both are set. |
| `AI_GATEWAY_API_KEY` | Calls Jev through Vercel AI Gateway. |

With neither, the mock runs. `TRIAGE_PROVIDER=typesafe|jev|mock` forces a
provider. The API's interactive docs are at http://localhost:8000/docs.

## Technical details

Two apps in one repository. The browser never talks to the API directly.

```
Browser  ->  TanStack Query  ->  Start server functions  ->  generated client  ->  FastAPI  ->  Jev
```

**`apps/api`**: FastAPI on Python 3.13, SQLModel on SQLite, httpx. Managed
with uv. The triage logic is a port with three adapters:

- `app/triage/port.py`: the contract every provider implements.
- `app/triage/typesafe.py`: TypeSafe's `POST /v1/systemone`. Their wire format
  calls the yes/no type `noul` and returns a confidence per answer.
- `app/triage/jev.py`: Vercel AI Gateway's `POST /v1/evaluate`, AI SDK naming.
- `app/triage/mock.py`: keyword heuristics.
- `app/triage/service.py`: turns any provider's answer into the stored result
  (argmax level, mean, refund threshold, provider, timestamp).
- `app/triage/factory.py`: picks the provider from the environment at startup.

Endpoints: `GET /meta`, `GET|POST /tickets`, `GET|PATCH|DELETE /tickets/{id}`,
`POST /tickets/{id}/move`, `POST /tickets/{id}/triage`. See
`apps/api/README.md`.

**`apps/web`**: TanStack Start with React 19, TanStack Router and Query,
Tailwind 4, shadcn/ui, Atlassian's pragmatic-drag-and-drop. Server functions
in `src/server/tickets.ts` wrap a client generated from the API's OpenAPI
document with `@hey-api/openapi-ts`. Query options and mutations, including
the optimistic move with rollback, live in `src/lib/queries.ts`. See
`apps/web/README.md`.

**Docker**: `apps/api/Dockerfile` (uv image, healthcheck on `/meta`, SQLite
volume), `apps/web/Dockerfile` (built from the repo root, ships the nitro
server output), `docker-compose.yml` wiring web to api.

**Developing** (toolchains on the host: Node 20+, pnpm 11.1.0, uv):

```bash
pnpm install && uv sync --directory apps/api
pnpm dev             # both dev servers with hot reload
pnpm test            # pytest then vitest, no network
pnpm lint            # ruff then eslint
pnpm export:openapi  # regenerate apps/api/openapi.json after an API change
pnpm generate:client # regenerate the web client from it
```

`CLAUDE.md` holds the working rules for this repo and `docs/context.md` the
decisions with their reasons.

## References

**Jev and TypeSafe AI**
- TypeSafe docs: https://docs.typesafe.ai/
- HTTP API reference (System One endpoint, request and response shapes): https://docs.typesafe.ai/api
- System One concept: https://docs.typesafe.ai/concepts/system-one
- Models: https://docs.typesafe.ai/models
- Python SDK (not used here, plain HTTP instead): https://docs.typesafe.ai/sdk/python
- Launch coverage: https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/

**Vercel AI Gateway route**
- Evaluation modality: https://vercel.com/docs/ai-gateway/modalities/evaluation
- TypeSafe-compatible endpoint: https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe
- AI SDK `experimental_evaluate` reference: https://ai-sdk.dev/docs/reference/ai-sdk-core/evaluate

**This app's API**
- Swagger UI when running: http://localhost:8000/docs
- ReDoc when running: http://localhost:8000/redoc
- Committed OpenAPI document: `apps/api/openapi.json`

**Stack**
- FastAPI: https://fastapi.tiangolo.com/
- SQLModel: https://sqlmodel.tiangolo.com/
- uv: https://docs.astral.sh/uv/
- TanStack Start: https://tanstack.com/start/latest
- TanStack Query: https://tanstack.com/query/latest
- @hey-api/openapi-ts: https://heyapi.dev/openapi-ts/get-started
- pragmatic-drag-and-drop: https://atlassian.design/components/pragmatic-drag-and-drop/about
- shadcn/ui: https://ui.shadcn.com/
- Tailwind CSS: https://tailwindcss.com/docs

**Self-hosted stand-in for Jev** (not used; Jev has no public weights)
- Jeff, an MIT server speaking the same System One contract: https://github.com/logan-markewich/jeff

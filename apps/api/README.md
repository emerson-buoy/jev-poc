# Jev Triage API

FastAPI backend for the board. Stores tickets in SQLite and triages them with
TypeSafe AI's Jev, called directly with a TypeSafe key or through Vercel AI
Gateway, or with a deterministic mock when no key is configured.

## Run

```bash
uv sync
uv run fastapi dev app/main.py --port 8000
```

Docs at http://localhost:8000/docs. The database `jev.db` is created and seeded
with ten sample tickets on first start.

## Configuration

Copy `.env.example` to `.env`. Every variable is optional.

| Variable                   | Default                                     | Meaning                                    |
| -------------------------- | ------------------------------------------- | ------------------------------------------ |
| `TRIAGE_PROVIDER`          | `auto`                                      | `auto`, `typesafe`, `jev` or `mock`        |
| `TYPESAFE_API_KEY`         | unset                                       | TypeSafe AI account key (direct Jev)       |
| `TYPESAFE_BASE_URL`        | `https://api.typesafe.ai/v1`                | TypeSafe API base                          |
| `TYPESAFE_MODEL_ID`        | `jev-latest`                                | Model id at TypeSafe                       |
| `AI_GATEWAY_API_KEY`       | unset                                       | Vercel AI Gateway key (Jev via gateway)    |
| `AI_GATEWAY_EVALUATE_URL`  | `https://ai-gateway.vercel.sh/v1/evaluate`  | Gateway evaluate endpoint                  |
| `JEV_MODEL_ID`             | `typesafe-ai/jev`                           | Model id at the gateway                    |
| `DATABASE_URL`             | `sqlite:///./jev.db`                        | SQLModel connection string                 |

`auto` picks `typesafe` when a TypeSafe key is set, else `jev` when a gateway
key is set, else `mock` with a warning. A forced provider without its key fails
at startup. Settings load a repo-root `.env` first and `apps/api/.env` second,
so the app-level file wins.

## Endpoints

| Method   | Path                      | Behaviour                                                   |
| -------- | ------------------------- | ----------------------------------------------------------- |
| `GET`    | `/meta`                   | Active provider and whether it is the mock                  |
| `GET`    | `/tickets`                | All tickets, oldest first                                   |
| `POST`   | `/tickets`                | Create in `new`                                             |
| `GET`    | `/tickets/{id}`           | One ticket                                                  |
| `PATCH`  | `/tickets/{id}`           | Update title, description or `department_override`          |
| `DELETE` | `/tickets/{id}`           | Remove                                                      |
| `POST`   | `/tickets/{id}/move`      | Set status. Into `triaged` runs triage once; into `new` discards it. 503 with `Retry-After` if the provider is unavailable, 502 if it rejects or answers unusably |
| `POST`   | `/tickets/{id}/triage`    | Re-run triage; the previous result goes to history          |

A ticket carries `triage` (Jev's result with probabilities, confidence and the
provider that produced it), `department_override` (a human decision),
`effective_department` (override if set, else Jev's choice) and `history`, the
discarded results newest first. Each history record holds the full result, the
override at the time, a `reason` (`moved_to_new` or `retriaged`) and
`discarded_at`. History rows live in the `triagerecord` table and are deleted
with their ticket.

## Triage providers

`app/triage/port.py` defines the contract and the failure types
(`ProviderUnavailable`, `ProviderRejected`, `MalformedResponse`).
`app/triage/http.py` is the single HTTP evaluator both Jev adapters use: one
client with the bearer header and timeout, error classification, closed on
shutdown. Three adapters implement the contract:

- `typesafe.py` posts the ticket as state with three questions (department
  choice, five-level urgency score, refund yes/no) to TypeSafe's
  `/v1/systemone`. TypeSafe calls the yes/no type `noul` and returns a
  confidence per answer, which is what the panel shows.
- `jev.py` sends the same questions to the gateway evaluate endpoint, which
  uses the AI SDK's `boolean` naming.
- `mock.py` scores keywords deterministically and synthesizes probabilities and
  confidence so the board looks the same either way. Results record
  `"provider": "mock"`.

`service.py` turns either answer into the stored result: 1-based urgency level
(argmax) and mean, refund flag at `REFUND_THRESHOLD` 0.5.

## Develop

```bash
uv run pytest -q                       # 79 tests, no network
uv run ruff check . && uv run ruff format .
uv run python -m scripts.export_openapi   # writes openapi.json for apps/web
```

Regenerate `openapi.json` whenever a schema or route changes, then run
`pnpm generate:client` at the repo root.

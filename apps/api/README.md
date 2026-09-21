# Jev Triage API

FastAPI backend for the board. Stores tickets in SQLite and triages them with
TypeSafe AI's Jev through Vercel AI Gateway, or with a deterministic mock when
no key is configured.

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
| `AI_GATEWAY_API_KEY`       | unset                                       | Vercel AI Gateway key                      |
| `TRIAGE_PROVIDER`          | `auto`                                      | `auto`, `jev` or `mock`                    |
| `JEV_MODEL_ID`             | `typesafe-ai/jev`                           | Evaluation model id                        |
| `AI_GATEWAY_EVALUATE_URL`  | `https://ai-gateway.vercel.sh/v1/evaluate`  | Gateway evaluate endpoint                  |
| `DATABASE_URL`             | `sqlite:///./jev.db`                        | SQLModel connection string                 |

`auto` picks `jev` when a key is set and `mock` otherwise, logging a warning.
`jev` without a key fails at startup.

## Endpoints

| Method   | Path                      | Behaviour                                                   |
| -------- | ------------------------- | ----------------------------------------------------------- |
| `GET`    | `/meta`                   | Active provider and whether it is the mock                  |
| `GET`    | `/tickets`                | All tickets, oldest first                                   |
| `POST`   | `/tickets`                | Create in `new`                                             |
| `GET`    | `/tickets/{id}`           | One ticket                                                  |
| `PATCH`  | `/tickets/{id}`           | Update title, description or `department_override`          |
| `DELETE` | `/tickets/{id}`           | Remove                                                      |
| `POST`   | `/tickets/{id}/move`      | Set status. Into `triaged` runs triage once; 502 on failure |
| `POST`   | `/tickets/{id}/triage`    | Re-run triage and replace the result                        |

A ticket carries `triage` (Jev's result with probabilities, confidence and the
provider that produced it), `department_override` (a human decision) and
`effective_department` (override if set, else Jev's choice).

## Triage providers

`app/triage/port.py` defines the contract. Two adapters implement it:

- `jev.py` posts the ticket as state with three questions (department choice,
  five-level urgency score, refund boolean) to the gateway evaluate endpoint.
- `mock.py` scores keywords deterministically and synthesizes probabilities and
  confidence so the board looks the same either way. Results record
  `"provider": "mock"`.

`service.py` turns either answer into the stored result: 1-based urgency level
(argmax) and mean, refund flag at `REFUND_THRESHOLD` 0.5.

## Develop

```bash
uv run pytest -q                       # 39 tests, no network
uv run ruff check . && uv run ruff format .
uv run python -m scripts.export_openapi   # writes openapi.json for apps/web
```

Regenerate `openapi.json` whenever a schema or route changes, then run
`pnpm generate:client` at the repo root.

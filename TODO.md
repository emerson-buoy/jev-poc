# TODO

Review of 2026-09-21, updated after PRs 1 to 7 merged. Each open item is one
small PR, tests first. Item numbers are stable so PR descriptions can point
at them. Nothing here changes a product decision recorded in
`docs/context.md` unless the item says so.

State: API 116 tests, web 26 tests, CI green on every push.

## Done

- [x] 15 Stricter Ruff and CI (#1): `S, RUF, PTH, PT, PERF, RET`; lint,
      tests, typecheck, build and Docker build on every push.
- [x] 1 Shared HTTP evaluator (#2): one `HttpEvaluator`, adapters only map
      wire formats, clients closed on shutdown.
- [x] 2 Typed failures (#3): `ProviderUnavailable` is 503 with
      `Retry-After`, everything else 502, fixed client text.
- [x] 3 Retries with a budget (#4): jittered backoff, `Retry-After`
      honoured, 10 s deadline, 3 s connect / 8 s read timeouts.
- [x] 16 Panel triage moves the card to Triaged, 9 one archive path (#5).
- [x] 4 Circuit breaker (#6): open after 5 unavailable answers, 30 s
      cooldown, one probe, `circuit` on `/meta`, red banner on the board.
- [x] 17 Server-sent events (#7): `GET /events`, in-process broadcaster,
      Start proxy route at `/api/events`, `useTicketEvents` hook.

## A. Structure (do first, the rest lands on it)

- [ ] 18 **Ticket service behind the router**
    - `routers/tickets.py` is 171 lines and no longer thin: it owns history
      loading, archiving, the save-and-publish sequence, the triage error
      mapping and the move rules. Items 7, 8, 11 and 12 would all pile more
      into it.
    - `app/tickets/service.py` with `TicketService(session, triage,
      broadcaster)` exposing `create`, `update`, `move`, `retriage`, `delete`,
      `read`, `list`; `app/tickets/errors.py` for the `TriageError` to
      `HTTPException` mapping. The router keeps route declarations and
      dependencies only. Behaviour unchanged; the existing 116 tests are the
      safety net, plus unit tests on the service with the mock provider.

## B. Realtime hardening

- [ ] 19 **EventSource reconnect and debounce**
    - `EventSource` reconnects on its own only after a dropped connection.
      On a non-200 answer, which is what the proxy returns when the API is
      down at page load, it closes for good. That tab then updates only on
      window focus and after its own mutations, silently.
    - In `useTicketEvents`, on `error` with `readyState === CLOSED`, dispose
      and reopen after a backoff (1 s doubling to 30 s), reset on `open`.
      Debounce invalidations to one per 100 ms so a burst of events causes one
      refetch. Tests with the fake `EventSource`: closed source is reopened,
      burst collapses to one fetch.

- [ ] 20 **Circuit state over the stream**
    - A tab that did not trigger the failing move sees no banner until it
      refocuses or moves a card itself, because `metaQuery` is
      `staleTime: Infinity` and only mutations invalidate it.
    - Broadcaster gains a second event name `meta.changed`; the breaker
      publishes it when its state flips (closed to open, open to half_open,
      back to closed). The hook invalidates `metaQuery` on it. Tests: breaker
      flip publishes once, hook invalidates meta on the event.

## C. Correctness under concurrency (on top of 18)

- [ ] 7 **Idempotency keys on the non-idempotent writes**
    - `POST /tickets` retried by the client after a network blip creates a
      duplicate. `POST /tickets/{id}/triage` double-clicked calls Jev twice and
      writes two history rows.
    - Accept `Idempotency-Key` on both. Store key, request hash and response
      for 24 h in SQLite; replay on a match, 409 on the same key with a
      different body. Missing header keeps today's behaviour; the web app sends
      a key per mutation in a follow-up.

- [ ] 8 **Optimistic locking on tickets**
    - Move and re-triage are read-modify-write with no version check. Two
      concurrent moves into Triaged both see `triage is None`, both call the
      provider, the second overwrites the first.
    - `version: int` on `Ticket`, bumped on save, `WHERE version = :expected`
      on the update, 409 on conflict. `If-Match` optional for clients.

## D. Persistence hygiene (on top of 18)

- [ ] 11 **History in one query**
    - `list_tickets` runs one history query per ticket. With server-sent
      events every board refetches the list on every change, so the N+1 is
      now multiplied by the number of open tabs.
    - One query on `ticket_id IN (...)` grouped in Python.

- [ ] 12 **Cascade delete in the database**
    - `delete_ticket` deletes history rows in a Python loop.
    - `ondelete="CASCADE"` on the foreign key plus `PRAGMA foreign_keys=ON`
      through an engine event for SQLite; drop the loop.

- [ ] 10 **Department as one enum**
    - Still defined three times: `DEPARTMENTS` tuple, `Department` Literal
      guarded by a runtime `assert`, and `department_override: str` on the
      model.
    - A `Department(StrEnum)` used by the model, schemas, questions and mock.
      Delete the assert.

## E. Operations

- [ ] 13 **Health endpoint that exercises the database**
    - Docker's healthcheck hits `/meta`, which only proves the process is up.
      The recorded gotcha (server alive, SQLite file gone, reads work, writes
      500) would pass it.
    - `GET /health` runs `SELECT 1` and a write inside a rolled-back
      transaction, 503 with the failing check named. Point the Dockerfile at
      it.

- [ ] 21 **Validated settings, fail fast at boot**
    - `triage_max_attempts=0`, a negative deadline or `triage_circuit_failures=0`
      are accepted and produce a provider that never calls or a circuit that
      is always open, discovered on the first move.
    - Pydantic `Field(ge=1)` / `Field(gt=0)` on the numeric settings; boot
      fails with the offending variable named.

- [ ] 22 **Observability**
    - The only triage log line is the failure warning. No latency, no attempt
      count, no request id, and a dropped SSE subscriber is silent.
    - One INFO line per triage: ticket id, provider, attempts, milliseconds,
      circuit state. WARNING when the broadcaster drops a subscriber. A
      request-id middleware that reads or mints `X-Request-ID` and puts it on
      the response and in every log record for that request. No new
      dependency: `logging` filters and a `contextvar`.

- [ ] 5 **Spend budget and usage recording**
    - TypeSafe returns `usage.input_tokens/output_tokens`; it is discarded.
      Nothing caps paid calls per day.
    - Store `usage` on `TriageResult`. `TRIAGE_DAILY_CALL_LIMIT` (unset means
      unlimited); over the cap, triage fails fast with 503 and a clear detail.
      Counter in SQLite so it survives restarts.

## F. Code standards and tests

- [ ] 14 **Strip comments and docstrings**
    - 13 lines remain across 9 files (`config.py`, `main.py`, `models.py`,
      `routers/tickets.py`, `schemas.py`, `seed.py`, `factory.py`, `mock.py`,
      `questions.py`). The urgency rubric commentary in `questions.py` is the
      only one that explains something the code cannot; move it to
      `docs/context.md`, which already describes the rubric.
    - Do this last so it does not conflict with anything in flight.

- [ ] 23 **Web hook tests**
    - `useMoveTicket`'s optimistic update and rollback, the toasts, and
      `useRetriage` are only exercised indirectly through the board test.
    - Hook tests with `renderHook`, a `QueryClientProvider` wrapper and a
      mocked `sonner`: optimistic status change, rollback on error, meta
      invalidation on settle, toast text for a triaged move.

- [ ] 24 **Coverage in CI**
    - Neither suite reports coverage; regressions in untested paths are
      invisible in review.
    - `pytest-cov` and `vitest --coverage` with a floor at today's numbers,
      uploaded as a job summary. No external service.

## Product decisions pending (not built without a yes)

- [ ] **Auto-triage on create.** With server-sent events in place the shape
      is: `POST /tickets` answers 201 in New immediately, triage runs in a
      background task, the card moves to Triaged when `tickets.changed`
      arrives. Failure has no toast channel today; it would need a
      `tickets.failed` event or the card staying in New with a marker.
- [ ] **Fallback provider chain** (item 6). Still conflicts with "a failed
      triage rejects the move". Recommendation unchanged: keep rejecting; 3
      and 4 cover the outage.
- [ ] **Gateway provider live check.** Jev is verified live through the
      `typesafe` provider only; the Vercel gateway path (`jev`) is covered by
      recorded responses. Needs a Vercel key. Nothing to build until then.

## Considered and not recommended

- **End-to-end SSE test through a real server.** Starlette's `TestClient`
  hangs on an endless stream and httpx's `ASGITransport` buffers the body.
  A uvicorn subprocess in tests would work but adds a port, a timeout and
  flakiness for a path already verified live and covered by the generator
  and publish-point tests.
- **Cache by content hash, queue or background triage on move, async
  httpx rewrite, Alembic, pagination, auth between web and api, closing
  port 8000 in compose.** Same reasoning as the first review; port 8000
  stays published for the Swagger UI.

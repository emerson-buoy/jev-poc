# API improvements

Review of `apps/api` on 2026-09-21. Each item is one small PR, tests first.
Numbers are proposed PR order; later items build on earlier ones where noted.
Nothing here changes a product decision recorded in `docs/context.md` unless
the item says so.

## A. Resilience against the provider

1. **Shared HTTP evaluator for both adapters** (prerequisite for 2, 3, 4)
   - `typesafe.py` and `jev.py` duplicate client setup, the post/try/except
     block, `_error_message` and the parse skeleton. Retries, timeouts and
     error classification would have to be written twice.
   - Extract one `post_evaluation(client, url, payload) -> dict` that owns the
     HTTP call and raises `TriageError`; adapters keep only wire-format mapping.
   - Also closes the `httpx.Client` on shutdown; today neither adapter is
     ever closed.

2. **Typed failures and correct status codes**
   - Every failure is `TriageError` and every one becomes HTTP 502, including
     upstream 429, 529, timeouts and our own parse errors. The UI cannot tell
     "try again" from "bug", and the 502 detail echoes up to 200 chars of the
     upstream body to the browser.
   - Subclasses: `ProviderUnavailable` (timeouts, 429, 5xx) -> 503 with
     `Retry-After`; `ProviderRejected` (401, 422) -> 502; `MalformedResponse`
     -> 502. Full upstream body goes to the log, the client gets a fixed message.

3. **Retries with a total budget**
   - A single transient 429 or 529 rejects the move. TypeSafe documents both
     codes; observed latency is 0.3 to 0.7 s, yet the timeout is a flat 30 s.
   - Retry `ProviderUnavailable` with exponential backoff and jitter, max 3
     attempts, honour `Retry-After`, under one deadline (`TRIAGE_DEADLINE_SECONDS`,
     default 10). Split httpx timeout into connect 3 s / read 8 s. Both settings
     in `config.py`. Never retry 4xx other than 429.

4. **Circuit breaker (fail fast during an outage)**
   - During a provider outage every move waits the full deadline before
     failing, and the threadpool fills with blocked requests.
   - After N consecutive `ProviderUnavailable` (default 5) open the circuit:
     fail in microseconds with 503 for a cooldown (default 30 s), then let one
     probe through. Expose `circuit: open|closed` on `/meta` so the banner can
     say "Jev unavailable" instead of "mock".

5. **Spend budget and usage recording**
   - TypeSafe returns `usage.input_tokens/output_tokens`; it is discarded.
     Nothing limits how many paid calls a day the board can make.
   - Store `usage` on `TriageResult`. Add `TRIAGE_DAILY_CALL_LIMIT` (unset =
     unlimited); when exceeded, triage fails fast with 503 and a clear detail.
     Counter lives in SQLite so it survives restarts.

6. **Fallback provider chain (product decision, ask before building)**
   - Graceful degradation option: `typesafe -> jev -> mock` on
     `ProviderUnavailable`, with the provider recorded on the result and a
     per-card "mock" marker in the UI. Conflicts with the recorded decision
     "a failed triage rejects the move". Listed so the choice is explicit;
     recommendation is to keep rejecting and rely on 3 and 4.

## B. Correctness under concurrency

7. **Idempotency keys on the non-idempotent writes**
   - `POST /tickets` retried by the client after a network blip creates a
     duplicate. `POST /tickets/{id}/triage` double-clicked calls Jev twice and
     writes two history rows.
   - Accept `Idempotency-Key` header on both. Store key, request hash and
     response for 24 h in SQLite; replay the stored response on a match,
     409 on the same key with a different body. Missing header keeps today's
     behaviour, so the web app can adopt it in a separate PR.

8. **Optimistic locking on tickets**
   - Move and re-triage are read-modify-write with no version check. Two
     concurrent moves into Triaged both see `triage is None` and both call the
     provider; the second overwrites the first.
   - Add `version: int` to `Ticket`, bump on save, and a
     `WHERE version = :expected` update. Conflict -> 409. Clients may send
     `If-Match: <version>`; without it the server still detects the lost
     update between its own read and write.

## C. Code hygiene and DRY

9. **One archive path**
   - `retriage_ticket` re-implements what `discard_triage` does (build
     `TriageRecord`, clear override). Call `discard_triage(..., RETRIAGED)`
     before `run_triage`; the session is not committed on failure so the
     rejected move leaves nothing behind.

10. **Department as one enum**
    - Departments are defined three times: `DEPARTMENTS` tuple in
      `questions.py`, `Department` Literal in `schemas.py` guarded by a
      runtime `assert` with a `noqa: S101` that Ruff never checks (S is not
      selected), and `department_override: str` untyped on the model.
    - A `Department(StrEnum)` used by the model, the schemas, the questions
      and the mock. Delete the assert.

11. **History loaded in one query**
    - `list_tickets` runs one history query per ticket (N+1). One query on
      `ticket_id IN (...)` grouped in Python. Trivial today, but the list
      endpoint is the one the board polls.

12. **Cascade delete in the database**
    - `delete_ticket` deletes history rows in a Python loop. Use
      `ondelete="CASCADE"` on the foreign key plus `PRAGMA foreign_keys=ON`
      for SQLite via an engine event, and drop the loop.

13. **Health endpoint that exercises the database**
    - Docker's healthcheck hits `/meta`, which only proves the process is up.
      The recorded gotcha (server alive, SQLite file gone, reads work, writes
      500) would pass it.
    - `GET /health` runs `SELECT 1` and a write inside a rolled-back
      transaction; returns 503 with the failing check named. Point the
      Dockerfile healthcheck at it. `/meta` stays for the banner.

14. **Strip comments and docstrings**
    - Your rule: zero comments unless the function is otherwise
      incomprehensible. Today there are module docstrings, function docstrings
      and inline comments across the package. Remove all; the only candidate to
      keep is the `noul` remark in `typesafe.py`, and even that reads fine
      once the constant is named `_YES_NO_TYPE = "noul"`.

## D. Tooling

15. **Stricter Ruff and a CI workflow**
    - No CI exists; `pnpm lint` and `pnpm test` run only by hand. Ruff selects
      `E, F, I, UP, B, SIM` only.
    - Add `S, RUF, PTH, PT, PERF, RET` and fix what they raise. GitHub Actions
      running `pnpm lint`, `pnpm test`, web typecheck and build, and
      `docker compose build` on every push.

## E. Board behaviour

16. **Triage cards should move to Triaged column**
    - "Triage now" in the detail panel (`POST /tickets/{id}/triage`) asks the
      provider and stores the result but leaves the card where it is. A card
      in New ends up classified while still sitting in the "waiting for
      triage" column, which contradicts the rule that Triaged is where
      classified cards live.
    - On a successful triage of a card whose status is `new`, set the status
      to `triaged` in the same transaction. Cards already in Triaged, In
      progress or Done keep their column on re-triage.
    - Tests: triage endpoint on a New ticket returns `status: "triaged"`; on a
      Done ticket returns `status: "done"`; a failed triage leaves status
      untouched. Web: the card leaves New after "Triage now" (queries are
      invalidated already, so the move needs no client change beyond the
      toast text).
    - Reported by Emerson on 2026-09-21: "today they dont".

## Considered and not recommended

- **Queue / background triage.** Contradicts "a card in Triaged always has a
  result" and the sub-second live latency makes it unnecessary. 3 and 4 cover
  the failure modes a queue would hide.
- **Cache by content hash.** Would skip the provider when a card re-enters
  Triaged with unchanged text. Saves a paid call but the recorded decision is
  that re-entering Triaged runs triage again, and explicit re-triage must
  bypass it anyway. Only worth it if 5 shows real spend.
- **Async httpx and async endpoints.** A rewrite for no measured gain; sync
  endpoints already run in the threadpool and `httpx.Client` is thread-safe.
- **Alembic migrations, pagination, auth between web and api.** Real for
  production, out of scope for a POC with ten tickets on localhost.

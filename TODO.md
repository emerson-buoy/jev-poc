# TODO

Deferred on purpose during the rescope on 2026-09-21.

- **Auto-triage on create.** Today triage runs when a card is moved into the
  Triaged column. Next: run it on `POST /tickets` so new cards arrive triaged,
  keeping the move trigger for cards created before that change.
- **Multi-user freshness.** The board refetches on window focus and after each
  mutation. Add server-sent events or websockets from the API so two open
  boards see each other's moves.
- **Real Jev run.** No AI Gateway key was available when this was built. The
  `jev` provider is covered by tests against recorded responses only. Verify
  against the live gateway once a key exists and adjust the confidence mapping
  if the metadata shape differs.

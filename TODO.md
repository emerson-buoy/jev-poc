# TODO

Deferred on purpose during the rescope on 2026-09-21.

- **Auto-triage on create.** Today triage runs when a card is moved into the
  Triaged column. Next: run it on `POST /tickets` so new cards arrive triaged,
  keeping the move trigger for cards created before that change.
- **Gateway provider live check.** Jev is verified live through TypeSafe's own
  API (`typesafe` provider). The Vercel gateway path (`jev` provider) is still
  covered by recorded responses only; verify it if a gateway key ever exists.

# CLAUDE.md

Project guidance for the Jev triage CLI. The global `~/.claude/CLAUDE.md` is
written for a Vue front-end and does not apply here beyond its critical rules
(no em-dash character U+2014, no generated-by lines, answer questions without changing
code, the user commits manually).

## What this is

A NestJS standalone CLI (no HTTP server) that triages support tickets with
TypeSafe AI's Jev model via the AI SDK `experimental_evaluate` API. See
`README.md` for usage. This file records the decisions and conventions.

## Stack

- Node 20+, pnpm, ESM (`"type": "module"`, `nodenext`, target ES2023).
- NestJS 12 with `@nestjs/cli` and its pinned TypeScript 6. `nest build` and
  `nest start` emit decorator metadata, so classes inject by type. Do not switch
  the runner to `tsx`: esbuild strips decorator metadata and type-based
  injection breaks at runtime (verified).
- `ai` 7.x. Only `experimental_evaluate` is used. Jev has no streaming; never
  add `streamText` or similar paths.
- `@nestjs/config` loads `.env`. Bare `dotenv` is not a dependency.
- Vitest 4 with globals, `*.spec.ts` beside sources, `@nestjs/testing` for
  module-level tests. `oxlint` and Prettier (single quotes, trailing commas)
  mirror the Nest 12 scaffold.

## Architecture

Ports and adapters, wired through the Nest IoC container in
`src/triage/triage.module.ts`.

- `domain/` holds interfaces, tokens and types only. No `@nestjs/*` or `ai`
  imports there.
- Interface ports are injected with `@Inject(TOKEN)` where `TOKEN` is a
  `Symbol` exported next to the interface. Concrete classes inject by type.
- `JevTriageEvaluator` is the only file that imports from `ai`. It maps the SDK
  result to the provider-neutral `TriageEvaluation` so the service never sees
  SDK types.
- `TriageService` owns the mapping rules: department is Jev's choice, urgency
  level is the 1-based argmax of the score distribution (rounded score plus one
  when no distribution comes back), urgency mean is the raw score plus one, and
  `refundRequested` is `probability >= REFUND_THRESHOLD` (0.5).
- `TriageCli` parses arguments with `node:util` `parseArgs`. No CLI framework.
- Presentation goes through the `TriagePresenter` port. `console.log` and
  `console.table` live only in `ConsoleTriagePresenter`.

## Config and failure

- `readAppConfig` in `src/config/app-config.ts` throws a one-line message when
  `AI_GATEWAY_API_KEY` is missing. It runs inside the `APP_CONFIG` factory, not
  in `ConfigModule.forRoot({ validate })`, because `forRoot` executes at module
  import time, outside any try/catch and before Vitest hooks can stub the env.
- `main.ts` boots with `logger: false` and `abortOnError: false` so boot errors
  reach the `catch` in `main.ts` and print as one line with exit code 1.
- Model id defaults to `typesafe-ai/jev` (the one id typed by
  `@ai-sdk/gateway`). `JEV_MODEL_ID` overrides it.

## API facts verified against ai@7.0.107

- `score` questions require `criteria`: an ordered array of at least two level
  descriptions. The urgency rubric is `URGENCY_LEVELS` in `triage-result.ts`.
- Answers are objects: choice `{ choice, probabilities? }`, score
  `{ score, probabilities? }` keyed by 0-based level index, boolean
  `{ probability }`. The spec's original `as string` casts do not compile.
- Per-question confidence, when present, is at
  `providerMetadata.typesafe.confidence`.

## Workflow

- Tests first. Every port has a fake in the specs; the suite never hits the
  network and needs no API key.
- Before calling work done: `pnpm test`, `pnpm lint`, `pnpm typecheck`,
  `pnpm build` must all pass.
- The user commits manually. Do not commit.
- Live gateway runs need a real key in `.env`. The example output in the README
  is illustrative; regenerate it from a real run when a key is available.

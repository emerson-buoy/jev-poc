# Jev Triage App

A small NestJS CLI that triages support tickets with TypeSafe AI's **Jev** model
through the AI SDK's `experimental_evaluate` API.

Jev does not generate prose. It evaluates a fixed set of typed questions against
one piece of state and returns typed answers with probabilities. For every ticket
the app asks three questions and prints the answers:

| Question           | Type      | Answer                                              |
| ------------------ | --------- | --------------------------------------------------- |
| `department`       | `choice`  | `billing`, `technical` or `general`, with a distribution |
| `urgency`          | `score`   | Level 1 to 5 over a five-step rubric, with a distribution |
| `refund_requested` | `boolean` | P(true); flagged as a refund at 0.5 or above        |

No streaming, no free-text parsing, no HTTP server, no persistence.

## Requirements

- Node.js 20 or newer
- pnpm
- A [Vercel AI Gateway](https://vercel.com/ai-gateway) API key

## Setup

```bash
pnpm install
cp .env.example .env
# edit .env and set AI_GATEWAY_API_KEY
```

`.env` is gitignored. `.env.example` is committed. The optional `JEV_MODEL_ID`
overrides the gateway model id, which defaults to `typesafe-ai/jev`.

## Run

Run all six sample tickets and print a summary table:

```bash
pnpm start
```

Run one sample ticket by id (`t1` to `t6`):

```bash
pnpm start -- --id t2
```

Triage arbitrary text:

```bash
pnpm start -- "My invoice was charged twice, please refund the duplicate."
```

`pnpm start` compiles with the Nest CLI on every run. For repeated runs, build
once and call the compiled entrypoint:

```bash
pnpm build
pnpm triage -- --id t1
```

If `AI_GATEWAY_API_KEY` is missing the app exits with code 1 and one line
telling you so, before any network call.

## Example output

One ticket. Numbers are illustrative and vary per run.

```
--- Refund request, billing ---
Ticket: I was charged twice for my October invoice. I'd like a refund for the dupli...
Department: billing
  billing 0.94 / technical 0.02 / general 0.04
Urgency: 3/5 (mean 3.1/5)
  1 0.03 / 2 0.14 / 3 0.55 / 4 0.24 / 5 0.04
Refund requested: yes (p=0.97)
Confidence: department 0.91 / urgency 0.72 / refund_requested 0.95
```

With no arguments, one block like the above is printed per sample ticket, then:

```
┌─────────┬────────────────────────────────────────┬─────────────┬─────────┬────────┐
│ (index) │ ticket                                 │ department  │ urgency │ refund │
├─────────┼────────────────────────────────────────┼─────────────┼─────────┼────────┤
│ 0       │ 'Outage, high urgency'                 │ 'technical' │ '5/5'   │ 'no'   │
│ 1       │ 'Refund request, billing'              │ 'billing'   │ '3/5'   │ 'yes'  │
│ 2       │ 'Low urgency, general question'        │ 'general'   │ '1/5'   │ 'no'   │
│ 3       │ 'Technical bug, medium urgency'        │ 'technical' │ '3/5'   │ 'no'   │
│ 4       │ 'Billing dispute, no refund requested' │ 'billing'   │ '2/5'   │ 'no'   │
│ 5       │ 'Angry customer, refund + urgent'      │ 'technical' │ '5/5'   │ 'yes'  │
└─────────┴────────────────────────────────────────┴─────────────┴─────────┴────────┘
```

## How the numbers are derived

- **Department** is the option Jev assigns the highest probability.
- **Urgency** comes back as a fractional 0-based position over the five rubric
  levels. The app shows the 1-based argmax level (`3/5`) and the 1-based mean
  (`3.1/5`). The raw score stays on the result object untouched.
- **Refund requested** is P(true) compared against `REFUND_THRESHOLD` (0.5) in
  `src/triage/application/triage.service.ts`.
- **Confidence** is TypeSafe's per-question confidence from
  `providerMetadata.typesafe.confidence`, printed only when present.

## Development

```bash
pnpm test        # vitest, no API key needed
pnpm test:watch
pnpm lint        # oxlint
pnpm format      # prettier
pnpm typecheck   # tsc --noEmit
pnpm build       # nest build -> dist/
```

The suite runs against a fake evaluator, so it never calls the gateway.

## Project layout

```
src/
  main.ts                          Boots a Nest standalone context and runs the CLI
  app.module.ts
  config/
    app-config.ts                  AppConfig, APP_CONFIG token, readAppConfig (fail fast)
    app-config.module.ts           @nestjs/config wiring
  triage/
    triage.module.ts               Binds ports to adapters
    domain/                        Ports and types, no framework or SDK imports
      ticket.ts                    Ticket, TicketSource port
      triage-evaluator.ts          TriageEvaluator port, provider-neutral TriageEvaluation
      triage-presenter.ts          TriagePresenter port
      triage-result.ts             TriageResult, Department, URGENCY_LEVELS rubric
    application/
      triage.service.ts            Maps an evaluation to a TriageResult
    infrastructure/
      jev-triage.evaluator.ts      Adapter over experimental_evaluate, owns the questions
      in-memory-ticket.source.ts   The six sample tickets
      console-triage.presenter.ts  Per-ticket blocks and the summary table
    cli/
      triage.cli.ts                Argument parsing with node:util parseArgs
```

Every consumer depends on a port. Swapping Jev for another evaluation model,
tickets for a file or an API, or the console for an HTTP response means adding
an adapter and rebinding it in `triage.module.ts`. See `CLAUDE.md` for the
design decisions behind this layout.

# Original build spec (2026-09-21)

The spec the project started from. It describes the NestJS CLI at commit
`5c3de9f`, which was replaced the same day by the board. Kept for the
question definitions, the sample tickets and the intent.

## Overview

A minimal CLI app that demonstrates TypeSafe AI's Jev model via the AI SDK's
`experimental_evaluate` API. The app takes a support ticket's text and returns
a structured, typed triage result: which department should own it, how urgent
it is, and whether a refund is being requested.

Jev does not generate prose. It evaluates a fixed set of typed questions
against a piece of state and returns typed answers with probabilities. No
streaming, no free-text parsing.

## Goals

- Working, runnable TypeScript CLI
- Calls Jev through AI SDK 7's `experimental_evaluate`
- Ships with a small set of sample tickets for demo and testing
- Clear, typed output (department, urgency score, refund boolean, probabilities)

## Non-goals

- No web UI (CLI only)
- No streaming (Jev does not support it)
- No database or persistence
- No batching of multiple tickets in one call

## Tech stack (as specified)

Node 18+, TypeScript, pnpm, `ai` 7.0.105+, model `typesafe-ai/jev` through
Vercel AI Gateway, `AI_GATEWAY_API_KEY` loaded with dotenv.

## Questions

```ts
questions: {
  department: {
    type: 'choice',
    instructions: 'Which team should handle this support ticket?',
    criteria: {
      billing: 'Payments, invoicing, refunds, billing disputes',
      technical: 'Bugs, outages, errors, integration or product issues',
      general: 'Anything else - account questions, feedback, unclear requests',
    },
  },
  urgency: {
    type: 'score',
    instructions:
      'Rate how urgent this ticket is on a 1-5 scale. 1 = no time pressure, 5 = active outage or blocking issue affecting the customer right now.',
  },
  refund_requested: {
    type: 'boolean',
    instructions: 'Is the customer explicitly asking for a refund?',
  },
}
```

Note: the real API requires `criteria` on score questions and returns answer
objects, not bare values. Both were corrected during the build.

## Sample tickets

| id | label | text |
| --- | --- | --- |
| t1 | Outage, high urgency | Our checkout page has been throwing a 500 error for the last 20 minutes. We're losing sales every minute this stays down. Please escalate immediately. |
| t2 | Refund request, billing | I was charged twice for my October invoice. I'd like a refund for the duplicate charge as soon as possible. |
| t3 | Low urgency, general question | Hi, just wondering if there's a way to change the display name on my account? No rush, whenever you get a chance. |
| t4 | Technical bug, medium urgency | The CSV export feature has been generating files with garbled characters for non-English names since yesterday's update. Not blocking us yet but it's affecting a few customers. |
| t5 | Billing dispute, no refund requested | I noticed my plan renewed at a higher price than I expected. Can someone explain the pricing change? I just want clarity, not necessarily a refund. |
| t6 | Angry customer, refund + urgent | This is the third time your app has crashed and lost my work. I want a full refund immediately and I want this fixed today. |

## CLI behavior (as specified)

- No args: run all sample tickets and print a results table
- One arg: treat it as raw ticket text and triage just that
- `--id <ticket_id>`: run a single sample ticket by id

## Acceptance criteria (as specified)

- `pnpm install && pnpm start` runs all 6 sample tickets without errors given a valid key
- `pnpm start -- --id t1` runs only that ticket
- `pnpm start -- "custom text"` triages arbitrary input
- TypeScript compiles cleanly
- No streaming code paths
- `.env` is gitignored; `.env.example` is committed

import { Inject, Injectable } from '@nestjs/common';
import {
  experimental_evaluate as evaluate,
  type Experimental_EvaluationQuestion,
} from 'ai';
import { APP_CONFIG, type AppConfig } from '../../config/app-config.js';
import type {
  TriageEvaluation,
  TriageEvaluator,
} from '../domain/triage-evaluator.js';
import { URGENCY_LEVELS } from '../domain/triage-result.js';

const TRIAGE_QUESTIONS = {
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
      'Rate how urgent this ticket is. Level 1 means no time pressure, level 5 means an active outage or blocking issue affecting the customer right now.',
    criteria: URGENCY_LEVELS,
  },
  refund_requested: {
    type: 'boolean',
    instructions: 'Is the customer explicitly asking for a refund?',
  },
} as const satisfies Record<string, Experimental_EvaluationQuestion>;

/** Adapter over the AI SDK evaluate call. Jev answers typed questions, no prose, no streaming. */
@Injectable()
export class JevTriageEvaluator implements TriageEvaluator {
  constructor(@Inject(APP_CONFIG) private readonly config: AppConfig) {}

  async evaluate(ticketText: string): Promise<TriageEvaluation> {
    const result = await evaluate({
      model: this.config.jevModelId,
      state: ticketText,
      questions: TRIAGE_QUESTIONS,
    });
    const { department, urgency, refund_requested } = result.answers;
    return {
      department: {
        choice: department.choice,
        probabilities: department.probabilities,
      },
      urgency: { score: urgency.score, probabilities: urgency.probabilities },
      refund: { probability: refund_requested.probability },
      confidence: readConfidence(result.providerMetadata),
    };
  }
}

function readConfidence(
  metadata: Record<string, unknown> | undefined,
): Record<string, number> | undefined {
  const typesafe = metadata?.typesafe;
  if (typeof typesafe !== 'object' || typesafe === null) return undefined;
  const confidence = (typesafe as Record<string, unknown>).confidence;
  if (typeof confidence !== 'object' || confidence === null) return undefined;
  const numeric = Object.entries(confidence).filter(
    (entry): entry is [string, number] => typeof entry[1] === 'number',
  );
  return numeric.length > 0 ? Object.fromEntries(numeric) : undefined;
}

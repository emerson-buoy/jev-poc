import { Inject, Injectable } from '@nestjs/common';
import {
  TRIAGE_EVALUATOR,
  type TriageEvaluation,
  type TriageEvaluator,
} from '../domain/triage-evaluator.js';
import type { TriageResult } from '../domain/triage-result.js';

/** P(true) at or above this counts as an explicit refund request. */
export const REFUND_THRESHOLD = 0.5;

@Injectable()
export class TriageService {
  constructor(
    @Inject(TRIAGE_EVALUATOR) private readonly evaluator: TriageEvaluator,
  ) {}

  async triage(ticketText: string): Promise<TriageResult> {
    const evaluation = await this.evaluator.evaluate(ticketText);
    const urgencyProbabilities = toOneBased(evaluation.urgency.probabilities);
    return {
      department: evaluation.department.choice,
      departmentProbabilities: evaluation.department.probabilities ?? {},
      urgencyScore: evaluation.urgency.score,
      urgencyLevel: pickLevel(evaluation.urgency),
      urgencyMean: evaluation.urgency.score + 1,
      urgencyProbabilities,
      refundRequested: evaluation.refund.probability >= REFUND_THRESHOLD,
      refundProbability: evaluation.refund.probability,
      confidence: evaluation.confidence,
    };
  }
}

function pickLevel(urgency: TriageEvaluation['urgency']): number {
  const entries = Object.entries(urgency.probabilities ?? {});
  if (entries.length === 0) return Math.round(urgency.score) + 1;
  const [index] = entries.reduce((best, entry) =>
    entry[1] > best[1] ? entry : best,
  );
  return Number(index) + 1;
}

function toOneBased(
  probabilities: Record<string, number> | undefined,
): Record<string, number> {
  return Object.fromEntries(
    Object.entries(probabilities ?? {}).map(([index, p]) => [
      String(Number(index) + 1),
      p,
    ]),
  );
}

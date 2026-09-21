import type { Department } from './triage-result.js';

export const TRIAGE_EVALUATOR = Symbol('TRIAGE_EVALUATOR');

/** Provider-neutral shape of one evaluation. Keeps SDK types out of the service. */
export interface TriageEvaluation {
  readonly department: {
    readonly choice: Department;
    readonly probabilities?: Partial<Record<Department, number>>;
  };
  readonly urgency: {
    readonly score: number;
    readonly probabilities?: Record<string, number>;
  };
  readonly refund: {
    readonly probability: number;
  };
  readonly confidence?: Record<string, number>;
}

export interface TriageEvaluator {
  evaluate(ticketText: string): Promise<TriageEvaluation>;
}

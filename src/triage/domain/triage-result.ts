export const DEPARTMENTS = ['billing', 'technical', 'general'] as const;

export type Department = (typeof DEPARTMENTS)[number];

/** Ordered rubric for the urgency score. Index 0 is level 1. */
export const URGENCY_LEVELS = [
  'No time pressure. Informational or cosmetic.',
  'Minor inconvenience with an easy workaround.',
  "Affecting some of the customer's work; workaround exists.",
  "Blocking part of the customer's work; no good workaround.",
  'Active outage or blocking issue affecting the customer right now.',
] as const;

export interface TriageResult {
  readonly department: Department;
  readonly departmentProbabilities: Partial<Record<Department, number>>;
  /** Raw provider score: fractional position in [0, levels - 1]. */
  readonly urgencyScore: number;
  /** 1-based integer level, the argmax of the distribution. */
  readonly urgencyLevel: number;
  /** 1-based fractional mean, the raw score shifted by one. */
  readonly urgencyMean: number;
  /** Distribution re-keyed to 1-based levels. Empty when not returned. */
  readonly urgencyProbabilities: Record<string, number>;
  readonly refundRequested: boolean;
  readonly refundProbability: number;
  /** Per-question provider confidence, when the provider returns it. */
  readonly confidence?: Record<string, number>;
}

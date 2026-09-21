import type { TriageResult } from './triage-result.js';

export const TRIAGE_PRESENTER = Symbol('TRIAGE_PRESENTER');

export interface TriageSummaryRow {
  readonly label: string;
  readonly result: TriageResult;
}

export interface TriagePresenter {
  presentResult(label: string, text: string, result: TriageResult): void;
  presentSummary(rows: readonly TriageSummaryRow[]): void;
  presentError(message: string): void;
}

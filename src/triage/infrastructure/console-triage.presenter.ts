import { Injectable } from '@nestjs/common';
import type {
  TriagePresenter,
  TriageSummaryRow,
} from '../domain/triage-presenter.js';
import type { TriageResult } from '../domain/triage-result.js';

const PREVIEW_LENGTH = 80;

@Injectable()
export class ConsoleTriagePresenter implements TriagePresenter {
  presentResult(label: string, text: string, result: TriageResult): void {
    console.log(`\n--- ${label} ---`);
    console.log(`Ticket: ${preview(text)}`);
    console.log(`Department: ${result.department}`);
    console.log(`  ${distribution(result.departmentProbabilities)}`);
    console.log(
      `Urgency: ${result.urgencyLevel}/5 (mean ${result.urgencyMean.toFixed(1)}/5)`,
    );
    console.log(`  ${distribution(result.urgencyProbabilities)}`);
    console.log(
      `Refund requested: ${yesNo(result.refundRequested)} (p=${result.refundProbability.toFixed(2)})`,
    );
    if (result.confidence) {
      console.log(`Confidence: ${distribution(result.confidence)}`);
    }
  }

  presentSummary(rows: readonly TriageSummaryRow[]): void {
    console.log('');
    console.table(
      rows.map(({ label, result }) => ({
        ticket: label,
        department: result.department,
        urgency: `${result.urgencyLevel}/5`,
        refund: yesNo(result.refundRequested),
      })),
    );
  }

  presentError(message: string): void {
    console.error(message);
  }
}

function preview(text: string): string {
  return text.length > PREVIEW_LENGTH
    ? `${text.slice(0, PREVIEW_LENGTH)}...`
    : text;
}

function yesNo(value: boolean): string {
  return value ? 'yes' : 'no';
}

function distribution(values: Record<string, number | undefined>): string {
  return Object.entries(values)
    .map(([key, p]) => `${key} ${(p ?? 0).toFixed(2)}`)
    .join(' / ');
}

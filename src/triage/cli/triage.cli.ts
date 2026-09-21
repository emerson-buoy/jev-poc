import { Inject, Injectable } from '@nestjs/common';
import { parseArgs } from 'node:util';
import { TriageService } from '../application/triage.service.js';
import {
  TICKET_SOURCE,
  type Ticket,
  type TicketSource,
} from '../domain/ticket.js';
import {
  TRIAGE_PRESENTER,
  type TriagePresenter,
  type TriageSummaryRow,
} from '../domain/triage-presenter.js';

const EXIT_OK = 0;
const EXIT_FAILURE = 1;

/**
 * No args: triage every sample ticket, then print a summary table.
 * --id <id>: triage one sample ticket.
 * Positional text: triage that text as a custom ticket.
 */
@Injectable()
export class TriageCli {
  constructor(
    private readonly triage: TriageService,
    @Inject(TICKET_SOURCE) private readonly tickets: TicketSource,
    @Inject(TRIAGE_PRESENTER) private readonly presenter: TriagePresenter,
  ) {}

  async run(argv: readonly string[]): Promise<number> {
    try {
      return await this.dispatch(argv);
    } catch (error) {
      this.presenter.presentError(`Error running triage: ${describe(error)}`);
      return EXIT_FAILURE;
    }
  }

  private async dispatch(argv: readonly string[]): Promise<number> {
    const { values, positionals } = parseArgs({
      args: [...argv],
      options: { id: { type: 'string' } },
      allowPositionals: true,
    });

    if (values.id !== undefined) {
      const ticket = this.tickets.findById(values.id);
      if (!ticket) {
        this.presenter.presentError(`No sample ticket with id "${values.id}"`);
        return EXIT_FAILURE;
      }
      await this.present(ticket);
      return EXIT_OK;
    }

    if (positionals.length > 0) {
      const text = positionals.join(' ');
      await this.present({ id: 'custom', label: 'Custom ticket', text });
      return EXIT_OK;
    }

    const rows: TriageSummaryRow[] = [];
    for (const ticket of this.tickets.all()) {
      rows.push({ label: ticket.label, result: await this.present(ticket) });
    }
    this.presenter.presentSummary(rows);
    return EXIT_OK;
  }

  private async present(ticket: Ticket) {
    const result = await this.triage.triage(ticket.text);
    this.presenter.presentResult(ticket.label, ticket.text, result);
    return result;
  }
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

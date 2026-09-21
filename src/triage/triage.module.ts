import { Module } from '@nestjs/common';
import { AppConfigModule } from '../config/app-config.module.js';
import { TriageService } from './application/triage.service.js';
import { TriageCli } from './cli/triage.cli.js';
import { TICKET_SOURCE } from './domain/ticket.js';
import { TRIAGE_EVALUATOR } from './domain/triage-evaluator.js';
import { TRIAGE_PRESENTER } from './domain/triage-presenter.js';
import { ConsoleTriagePresenter } from './infrastructure/console-triage.presenter.js';
import { InMemoryTicketSource } from './infrastructure/in-memory-ticket.source.js';
import { JevTriageEvaluator } from './infrastructure/jev-triage.evaluator.js';

@Module({
  imports: [AppConfigModule],
  providers: [
    { provide: TRIAGE_EVALUATOR, useClass: JevTriageEvaluator },
    { provide: TICKET_SOURCE, useClass: InMemoryTicketSource },
    { provide: TRIAGE_PRESENTER, useClass: ConsoleTriagePresenter },
    TriageService,
    TriageCli,
  ],
  exports: [TriageCli],
})
export class TriageModule {}

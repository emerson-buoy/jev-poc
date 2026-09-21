import { Module } from '@nestjs/common';
import { TriageModule } from './triage/triage.module.js';

@Module({
  imports: [TriageModule],
})
export class AppModule {}

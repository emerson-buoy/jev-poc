import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { TriageCli } from './triage/cli/triage.cli.js';

async function bootstrap(): Promise<number> {
  const app = await NestFactory.createApplicationContext(AppModule, {
    logger: false,
    abortOnError: false,
  });
  try {
    return await app.get(TriageCli).run(process.argv.slice(2));
  } finally {
    await app.close();
  }
}

try {
  process.exitCode = await bootstrap();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}

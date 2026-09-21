import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { APP_CONFIG, type AppConfig, readAppConfig } from './app-config.js';

const ENV_KEYS = ['AI_GATEWAY_API_KEY', 'JEV_MODEL_ID'] as const;

/** Loads .env through @nestjs/config and exposes a validated, typed AppConfig. */
@Module({
  imports: [ConfigModule.forRoot()],
  providers: [
    {
      provide: APP_CONFIG,
      inject: [ConfigService],
      useFactory: (config: ConfigService): AppConfig =>
        readAppConfig(
          Object.fromEntries(
            ENV_KEYS.map((key) => [key, config.get<string>(key)]),
          ),
        ),
    },
  ],
  exports: [APP_CONFIG],
})
export class AppConfigModule {}

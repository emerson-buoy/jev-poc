export const APP_CONFIG = Symbol('APP_CONFIG');

export const DEFAULT_JEV_MODEL_ID = 'typesafe-ai/jev';

export interface AppConfig {
  readonly aiGatewayApiKey: string;
  readonly jevModelId: string;
}

export type EnvSource = Readonly<Record<string, string | undefined>>;

/** Builds the config once at boot. Fails fast, before any gateway call. */
export function readAppConfig(env: EnvSource): AppConfig {
  const aiGatewayApiKey = env.AI_GATEWAY_API_KEY;
  if (!aiGatewayApiKey) {
    throw new Error(
      'AI_GATEWAY_API_KEY is not set. Copy .env.example to .env and add your Vercel AI Gateway key.',
    );
  }
  return {
    aiGatewayApiKey,
    jevModelId: env.JEV_MODEL_ID || DEFAULT_JEV_MODEL_ID,
  };
}

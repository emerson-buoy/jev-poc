import { DEFAULT_JEV_MODEL_ID, readAppConfig } from './app-config.js';

describe('readAppConfig', () => {
  it('throws a readable message when AI_GATEWAY_API_KEY is missing', () => {
    expect(() => readAppConfig({})).toThrow(/AI_GATEWAY_API_KEY/);
  });

  it('throws when AI_GATEWAY_API_KEY is empty', () => {
    expect(() => readAppConfig({ AI_GATEWAY_API_KEY: '' })).toThrow(
      /AI_GATEWAY_API_KEY/,
    );
  });

  it('defaults the model id to the gateway Jev id', () => {
    expect(readAppConfig({ AI_GATEWAY_API_KEY: 'k' })).toEqual({
      aiGatewayApiKey: 'k',
      jevModelId: DEFAULT_JEV_MODEL_ID,
    });
    expect(DEFAULT_JEV_MODEL_ID).toBe('typesafe-ai/jev');
  });

  it('honours a JEV_MODEL_ID override', () => {
    expect(
      readAppConfig({ AI_GATEWAY_API_KEY: 'k', JEV_MODEL_ID: 'typesafe-ai/x' })
        .jevModelId,
    ).toBe('typesafe-ai/x');
  });
});

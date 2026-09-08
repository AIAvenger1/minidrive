import type { loadConfig as LoadConfig } from './config';

const baseEnv = {
  DATABASE_URL: 'postgres://test',
  JWT_SECRET: 'secret',
  S3_ENDPOINT: 'http://localhost:9000',
  S3_ACCESS_KEY: 'key',
  S3_SECRET_KEY: 'secret-key',
};

function freshLoadConfig(): typeof LoadConfig {
  jest.resetModules();
  return require('./config').loadConfig;
}

describe('loadConfig', () => {
  it('falls back to the default port when PORT is not a number', () => {
    const loadConfig = freshLoadConfig();
    const config = loadConfig({ ...baseEnv, PORT: 'abc' });
    expect(config.port).toBe(3000);
  });

  it('disables swagger when SWAGGER_ENABLED is false', () => {
    const loadConfig = freshLoadConfig();
    const config = loadConfig({ ...baseEnv, SWAGGER_ENABLED: 'false' });
    expect(config.swaggerEnabled).toBe(false);
  });

  it('enables swagger when SWAGGER_ENABLED is unset', () => {
    const loadConfig = freshLoadConfig();
    const config = loadConfig({ ...baseEnv });
    expect(config.swaggerEnabled).toBe(true);
  });
});

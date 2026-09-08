import { loadConfig } from './config';

describe('loadConfig', () => {
  it('falls back to the default port when PORT is not a number', () => {
    const config = loadConfig({
      DATABASE_URL: 'postgres://test',
      JWT_SECRET: 'secret',
      S3_ENDPOINT: 'http://localhost:9000',
      S3_ACCESS_KEY: 'key',
      S3_SECRET_KEY: 'secret-key',
      PORT: 'abc',
    });
    expect(config.port).toBe(3000);
  });
});

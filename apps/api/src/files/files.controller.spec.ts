import { BadRequestException } from '@nestjs/common';

describe('FilesController.upload', () => {
  const originalEnv = { ...process.env };

  beforeAll(() => {
    process.env.DATABASE_URL = 'postgres://test';
    process.env.JWT_SECRET = 'test-secret';
    process.env.S3_ENDPOINT = 'http://localhost:9000';
    process.env.S3_ACCESS_KEY = 'test-key';
    process.env.S3_SECRET_KEY = 'test-secret-key';
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it('rejects an upload with no file part', () => {
    const { FilesController } =
      require('./files.controller') as typeof import('./files.controller');
    const files = { upsert: jest.fn() };
    const controller = new FilesController(files as never);
    const user = { id: 'u1', username: 'bohdan' };
    expect(() => controller.upload(user, undefined as never)).toThrow(
      BadRequestException,
    );
    expect(files.upsert).not.toHaveBeenCalled();
  });
});

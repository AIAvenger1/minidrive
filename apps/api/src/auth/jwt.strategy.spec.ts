import { UnauthorizedException } from '@nestjs/common';
import { JwtStrategy } from './jwt.strategy';

describe('JwtStrategy.validate', () => {
  const originalEnv = { ...process.env };
  const users = { findById: jest.fn() };

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

  beforeEach(() => jest.clearAllMocks());

  it('resolves the current user from the database', async () => {
    users.findById.mockResolvedValue({ id: 'u1', username: 'bohdan' });
    const strategy = new JwtStrategy(users as never);
    const result = await strategy.validate({ sub: 'u1', username: 'bohdan' });
    expect(result).toEqual({ id: 'u1', username: 'bohdan' });
    expect(users.findById).toHaveBeenCalledWith('u1');
  });

  it('rejects a token for a user that no longer exists', async () => {
    users.findById.mockResolvedValue(null);
    const strategy = new JwtStrategy(users as never);
    await expect(
      strategy.validate({ sub: 'gone', username: 'bohdan' }),
    ).rejects.toBeInstanceOf(UnauthorizedException);
  });
});

import { ConflictException, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  const users = {
    findByUsername: jest.fn(),
    create: jest.fn(),
    verify: jest.fn(),
  };
  const jwt = new JwtService({ secret: 'test-secret', signOptions: { expiresIn: '24h' } });
  const service = new AuthService(users as never, jwt);

  beforeEach(() => jest.clearAllMocks());

  it('registers a new user and returns a token', async () => {
    users.findByUsername.mockResolvedValue(null);
    users.create.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    const res = await service.register({ username: 'bohdan', password: 'secret123' });
    expect(res.user).toEqual({ id: 'u1', username: 'bohdan' });
    expect(jwt.verify(res.accessToken)).toMatchObject({ sub: 'u1', username: 'bohdan' });
  });

  it('rejects a taken username with 409', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1' });
    await expect(service.register({ username: 'bohdan', password: 'secret123' })).rejects.toBeInstanceOf(ConflictException);
  });

  it('rejects a wrong password with 401', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    users.verify.mockResolvedValue(false);
    await expect(service.login({ username: 'bohdan', password: 'nope' })).rejects.toBeInstanceOf(UnauthorizedException);
  });

  it('logs in with a correct password', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    users.verify.mockResolvedValue(true);
    const res = await service.login({ username: 'bohdan', password: 'secret123' });
    expect(res.accessToken).toBeTruthy();
  });
});

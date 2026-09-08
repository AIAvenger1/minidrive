import { UsersService } from './users.service';

describe('UsersService', () => {
  const prisma = { user: { findUnique: jest.fn(), create: jest.fn() } };
  const service = new UsersService(prisma as never);

  beforeEach(() => jest.clearAllMocks());

  it('hashes the password on create and never stores it in clear', async () => {
    prisma.user.create.mockImplementation(async ({ data }: { data: { username: string; passwordHash: string } }) => ({ id: 'u1', ...data }));
    const user = await service.create('bohdan', 'secret123');
    expect(user.passwordHash).not.toBe('secret123');
    expect(await service.verify('secret123', user.passwordHash)).toBe(true);
    expect(await service.verify('wrong', user.passwordHash)).toBe(false);
  });

  it('looks up by username', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 'u1', username: 'bohdan' });
    expect(await service.findByUsername('bohdan')).toMatchObject({ id: 'u1' });
    expect(prisma.user.findUnique).toHaveBeenCalledWith({ where: { username: 'bohdan' } });
  });
});

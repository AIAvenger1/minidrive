import { NotFoundException } from '@nestjs/common';
import { FilesService } from './files.service';

const owner = { id: 'u1', username: 'bohdan' };
const editor = { id: 'u2', username: 'olena' };
const existing = {
  id: 'f1', ownerId: 'u1', name: 'report.cs', extension: 'cs', size: 3, storageKey: 'users/u1/f1',
  createdAt: new Date('2026-09-01T10:00:00Z'), updatedAt: new Date('2026-09-01T10:00:00Z'),
  uploadedById: 'u1', modifiedById: 'u1',
  uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' },
};

describe('FilesService.upsert', () => {
  const prisma = { fileEntry: { findUnique: jest.fn(), findMany: jest.fn(), create: jest.fn(), update: jest.fn(), delete: jest.fn() } };
  const storage = { putObject: jest.fn(), getObject: jest.fn(), deleteObject: jest.fn() };
  const service = new FilesService(prisma as never, storage as never);
  const upload = { originalname: 'report.cs', buffer: Buffer.from('new!'), mimetype: 'text/plain', size: 4 };

  beforeEach(() => jest.clearAllMocks());

  it('creates a new entry with uploadedBy = modifiedBy = caller', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue(null);
    prisma.fileEntry.create.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({
      ...existing, ...data, id: 'f9', storageKey: 'users/u1/f9', uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' },
    }));
    prisma.fileEntry.update.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({ ...existing, ...data, id: 'f9', uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' } }));
    const dto = await service.upsert(owner, upload);
    expect(dto.uploadedBy).toBe('bohdan');
    expect(dto.modifiedBy).toBe('bohdan');
    expect(storage.putObject).toHaveBeenCalledWith('users/u1/f9', upload.buffer, 'text/plain');
  });

  it('overwrites an existing name: same id and key, new bytes, modifiedBy = caller', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue(existing);
    prisma.fileEntry.update.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({
      ...existing, ...data, modifiedBy: { username: 'olena' },
    }));
    const dto = await service.upsert(editor, upload);
    expect(dto.id).toBe('f1');
    expect(dto.uploadedBy).toBe('bohdan');
    expect(dto.modifiedBy).toBe('olena');
    expect(storage.putObject).toHaveBeenCalledWith('users/u1/f1', upload.buffer, 'text/plain');
    expect(prisma.fileEntry.update.mock.calls[0][0].data).toMatchObject({ size: 4, modifiedById: 'u2' });
    expect(prisma.fileEntry.create).not.toHaveBeenCalled();
  });

  it('refuses to read a file from another space', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue({ ...existing, ownerId: 'someone-else' });
    await expect(service.getContent('u1', 'f1')).rejects.toBeInstanceOf(NotFoundException);
  });

  it('removes the created row when the upload to storage fails', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue(null);
    prisma.fileEntry.create.mockResolvedValue({ ...existing, id: 'f9', storageKey: '' });
    storage.putObject.mockRejectedValue(new Error('storage down'));
    await expect(service.upsert(owner, upload)).rejects.toThrow('storage down');
    expect(prisma.fileEntry.delete).toHaveBeenCalledWith({ where: { id: 'f9' } });
    expect(prisma.fileEntry.update).not.toHaveBeenCalled();
  });

  it('deletes the row before the object', async () => {
    const order: string[] = [];
    prisma.fileEntry.findUnique.mockResolvedValue(existing);
    prisma.fileEntry.delete.mockImplementation(async () => {
      order.push('prisma.delete');
    });
    storage.deleteObject.mockImplementation(async () => {
      order.push('storage.delete');
    });
    await service.delete('u1', 'f1');
    expect(order).toEqual(['prisma.delete', 'storage.delete']);
  });
});

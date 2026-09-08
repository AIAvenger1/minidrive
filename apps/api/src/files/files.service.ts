import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { FileEntry } from '@prisma/client';
import { extensionOf } from '@minidrive/shared';
import { Readable } from 'stream';
import { basename } from 'path';
import { JwtUser } from '../auth/jwt.strategy';
import { PrismaService } from '../prisma/prisma.service';
import { StorageService } from '../storage/storage.service';
import { FileDto } from './file.dto';

type Upload = { originalname: string; buffer: Buffer; mimetype: string; size: number };
type EntryWithUsers = FileEntry & { uploadedBy: { username: string }; modifiedBy: { username: string } };

const withUsers = { uploadedBy: { select: { username: true } }, modifiedBy: { select: { username: true } } };

@Injectable()
export class FilesService {
  constructor(private readonly prisma: PrismaService, private readonly storage: StorageService) {}

  async listFor(ownerId: string): Promise<FileDto[]> {
    const rows = await this.prisma.fileEntry.findMany({ where: { ownerId }, include: withUsers });
    return rows.map((r) => this.toDto(r));
  }

  async upsert(owner: JwtUser, file: Upload): Promise<FileDto> {
    const name = file.originalname;
    if (basename(name) !== name || name === '.' || name === '..' || !name.trim() || name.includes('/') || name.includes('\\')) {
      throw new BadRequestException('Invalid file name');
    }
    const found = await this.prisma.fileEntry.findUnique({
      where: { ownerId_name: { ownerId: owner.id, name } },
      include: withUsers,
    });
    if (found) {
      await this.storage.putObject(found.storageKey, file.buffer, file.mimetype);
      const updated = await this.prisma.fileEntry.update({
        where: { id: found.id },
        data: { size: file.size, updatedAt: new Date(), modifiedById: owner.id },
        include: withUsers,
      });
      return this.toDto(updated);
    }
    const created = await this.prisma.fileEntry.create({
      data: {
        ownerId: owner.id, name, extension: extensionOf(name), size: file.size, storageKey: '',
        uploadedById: owner.id, modifiedById: owner.id,
      },
      include: withUsers,
    });
    const storageKey = `users/${owner.id}/${created.id}`;
    try {
      await this.storage.putObject(storageKey, file.buffer, file.mimetype);
      const saved = await this.prisma.fileEntry.update({ where: { id: created.id }, data: { storageKey }, include: withUsers });
      return this.toDto(saved);
    } catch (err) {
      await this.prisma.fileEntry.delete({ where: { id: created.id } });
      throw err;
    }
  }

  async getContent(ownerId: string, id: string): Promise<{ stream: Readable; mimeType: string; size?: number; name: string }> {
    const entry = await this.findOwned(ownerId, id);
    const object = await this.storage.getObject(entry.storageKey);
    return { ...object, name: entry.name };
  }

  async delete(ownerId: string, id: string): Promise<void> {
    const entry = await this.findOwned(ownerId, id);
    await this.prisma.fileEntry.delete({ where: { id } });
    await this.storage.deleteObject(entry.storageKey);
  }

  private async findOwned(ownerId: string, id: string): Promise<FileEntry> {
    const entry = await this.prisma.fileEntry.findUnique({ where: { id } });
    if (!entry || entry.ownerId !== ownerId) throw new NotFoundException('File not found');
    return entry;
  }

  private toDto(row: EntryWithUsers): FileDto {
    return {
      id: row.id,
      name: row.name,
      extension: row.extension,
      size: row.size,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
      uploadedBy: row.uploadedBy.username,
      modifiedBy: row.modifiedBy.username,
    };
  }
}

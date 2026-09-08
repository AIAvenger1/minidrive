import type { FileDto } from './types';

export function makeFileDto(overrides: Partial<FileDto> = {}): FileDto {
  return {
    id: 'id-1',
    name: 'file.txt',
    extension: 'txt',
    size: 10,
    createdAt: '2026-09-01T10:00:00.000Z',
    updatedAt: '2026-09-01T10:00:00.000Z',
    uploadedBy: 'bohdan',
    modifiedBy: 'bohdan',
    ...overrides,
  };
}

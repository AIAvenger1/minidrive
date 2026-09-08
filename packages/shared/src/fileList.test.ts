import { describe, expect, it } from 'vitest';
import { extensionOf, filterByType, sortByName } from './fileList';
import type { FileDto } from './types';

const file = (name: string, i = 0): FileDto => ({
  id: `id-${name}-${i}`,
  name,
  extension: extensionOf(name),
  size: 10,
  createdAt: '2026-09-01T10:00:00.000Z',
  updatedAt: '2026-09-01T10:00:00.000Z',
  uploadedBy: 'bohdan',
  modifiedBy: 'bohdan',
});

describe('sortByName', () => {
  const files = [file('report.cs'), file('Alpha.png'), file('beta.cpp'), file('file10.txt'), file('file2.txt')];

  it('sorts ascending, case-insensitively and numerically', () => {
    expect(sortByName(files, 'asc').map((f) => f.name)).toEqual([
      'Alpha.png', 'beta.cpp', 'file2.txt', 'file10.txt', 'report.cs',
    ]);
  });

  it('sorts descending', () => {
    expect(sortByName(files, 'desc').map((f) => f.name)).toEqual([
      'report.cs', 'file10.txt', 'file2.txt', 'beta.cpp', 'Alpha.png',
    ]);
  });

  it('does not mutate the input and is stable for equal names', () => {
    const dup = [file('same.txt', 1), file('same.txt', 2)];
    const sorted = sortByName(dup, 'asc');
    expect(sorted.map((f) => f.id)).toEqual(['id-same.txt-1', 'id-same.txt-2']);
    expect(dup.map((f) => f.id)).toEqual(['id-same.txt-1', 'id-same.txt-2']);
    expect(sorted).not.toBe(dup);
  });
});

describe('filterByType', () => {
  const files = [file('main.cpp'), file('logo.PNG'), file('report.cs'), file('photo.jpg'), file('notes')];

  it('returns everything for "all"', () => {
    expect(filterByType(files, 'all')).toHaveLength(5);
  });

  it('keeps only .cpp and .png for "cpp-png", case-insensitively', () => {
    expect(filterByType(files, 'cpp-png').map((f) => f.name)).toEqual(['main.cpp', 'logo.PNG']);
  });
});

describe('extensionOf', () => {
  it('returns the lower-cased extension without the dot', () => {
    expect(extensionOf('Photo.JPG')).toBe('jpg');
    expect(extensionOf('archive.tar.gz')).toBe('gz');
    expect(extensionOf('README')).toBe('');
    expect(extensionOf('.env')).toBe('');
  });
});

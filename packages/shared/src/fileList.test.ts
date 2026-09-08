import { describe, expect, it } from 'vitest';
import { extensionOf, filterByType, isSafeFileName, isSyncableName, sortByName } from './fileList';
import { makeFileDto } from './testFixtures';
import type { FileDto } from './types';

const file = (name: string, i = 0): FileDto => makeFileDto({ id: `id-${name}-${i}`, name, extension: extensionOf(name) });

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

  it('returns a copy for "all", not the same array', () => {
    const result = filterByType(files, 'all');
    expect(result).not.toBe(files);
    expect(result).toEqual(files);
  });

  it('keeps only .cpp files for "cpp"', () => {
    expect(filterByType(files, 'cpp').map((f) => f.name)).toEqual(['main.cpp']);
  });

  it('keeps only .png files for "png", case-insensitively', () => {
    expect(filterByType(files, 'png').map((f) => f.name)).toEqual(['logo.PNG']);
  });
});

describe('extensionOf', () => {
  it('returns the lower-cased extension without the dot', () => {
    expect(extensionOf('Photo.JPG')).toBe('jpg');
    expect(extensionOf('archive.tar.gz')).toBe('gz');
    expect(extensionOf('README')).toBe('');
    expect(extensionOf('.env')).toBe('');
  });

  it('returns empty for a name that ends with a bare dot', () => {
    expect(extensionOf('file.')).toBe('');
  });
});

describe('isSafeFileName', () => {
  it('rejects separators, dot, dot-dot and blank names', () => {
    expect(isSafeFileName('a/b.txt')).toBe(false);
    expect(isSafeFileName('a\\b.txt')).toBe(false);
    expect(isSafeFileName('.')).toBe(false);
    expect(isSafeFileName('..')).toBe(false);
    expect(isSafeFileName('   ')).toBe(false);
  });

  it('accepts a leading dot and a plain name', () => {
    expect(isSafeFileName('.env')).toBe(true);
    expect(isSafeFileName('report.cs')).toBe(true);
  });
});

describe('isSyncableName', () => {
  it('rejects unsafe names and dot-prefixed names', () => {
    expect(isSyncableName('a/b.txt')).toBe(false);
    expect(isSyncableName('.env')).toBe(false);
  });

  it('accepts a plain name', () => {
    expect(isSyncableName('report.cs')).toBe(true);
  });
});

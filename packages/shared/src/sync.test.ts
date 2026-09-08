import { describe, expect, it } from 'vitest';
import { computeSyncPlan } from './sync';
import type { FileDto, LocalFileInfo } from './types';

const t0 = Date.parse('2026-09-01T10:00:00.000Z');
const remote = (name: string, size: number, updatedAtMs: number): FileDto => ({
  id: `r-${name}`, name, extension: '', size, createdAt: '', updatedAt: new Date(updatedAtMs).toISOString(), uploadedBy: 'a', modifiedBy: 'a',
});
const local = (name: string, size: number, mtime: number): LocalFileInfo => ({ name, size, mtime });

describe('computeSyncPlan', () => {
  it('uploads files that exist only locally', () => {
    const plan = computeSyncPlan([local('a.txt', 5, t0)], []);
    expect(plan.uploads.map((a) => a.name)).toEqual(['a.txt']);
    expect(plan.downloads).toEqual([]);
  });

  it('downloads files that exist only remotely', () => {
    const plan = computeSyncPlan([], [remote('b.png', 5, t0)]);
    expect(plan.downloads.map((a) => a.name)).toEqual(['b.png']);
  });

  it('skips identical files within the clock skew', () => {
    const plan = computeSyncPlan([local('c.cs', 7, t0 + 1500)], [remote('c.cs', 7, t0)]);
    expect(plan.skipped.map((a) => a.name)).toEqual(['c.cs']);
  });

  it('uploads when the local copy is newer', () => {
    const plan = computeSyncPlan([local('d.cpp', 9, t0 + 60_000)], [remote('d.cpp', 8, t0)]);
    expect(plan.uploads[0]).toMatchObject({ name: 'd.cpp', kind: 'upload' });
  });

  it('downloads when the remote copy is newer', () => {
    const plan = computeSyncPlan([local('e.jpg', 9, t0)], [remote('e.jpg', 8, t0 + 60_000)]);
    expect(plan.downloads[0]).toMatchObject({ name: 'e.jpg', kind: 'download' });
  });

  it('treats a size difference within the skew window as a change', () => {
    const plan = computeSyncPlan([local('f.txt', 10, t0 + 500)], [remote('f.txt', 11, t0)]);
    expect(plan.uploads.map((a) => a.name)).toEqual(['f.txt']);
  });
});

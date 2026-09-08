import { describe, expect, it } from 'vitest';
import { computeSyncPlan, emptySyncReport, failedSyncReport, runSyncPlan } from './sync';
import { makeFileDto } from './testFixtures';
import type { FileDto, LocalFileInfo, SyncPlan } from './types';

const t0 = Date.parse('2026-09-01T10:00:00.000Z');
const remote = (name: string, size: number, updatedAtMs: number): FileDto =>
  makeFileDto({ id: `r-${name}`, name, extension: '', size, updatedAt: new Date(updatedAtMs).toISOString() });
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

  it('downloads instead of throwing when the remote timestamp cannot be parsed', () => {
    const plan = computeSyncPlan([local('g.txt', 5, t0)], [{ ...remote('g.txt', 5, t0), updatedAt: 'not-a-date' }]);
    expect(plan.downloads).toEqual([{ kind: 'download', name: 'g.txt', reason: 'invalid remote timestamp' }]);
  });
});

describe('emptySyncReport', () => {
  it('starts every counter at zero with no errors', () => {
    expect(emptySyncReport()).toEqual({ uploaded: 0, downloaded: 0, skipped: 0, failed: 0, errors: [] });
  });
});

describe('failedSyncReport', () => {
  it('records a single failure with the given message', () => {
    expect(failedSyncReport('boom')).toEqual({ uploaded: 0, downloaded: 0, skipped: 0, failed: 1, errors: ['boom'] });
  });
});

describe('runSyncPlan', () => {
  it('counts uploads, downloads and skipped from the plan', async () => {
    const plan: SyncPlan = {
      uploads: [{ kind: 'upload', name: 'a.txt', reason: 'only local' }],
      downloads: [{ kind: 'download', name: 'b.png', reason: 'only remote' }],
      skipped: [{ kind: 'skip', name: 'c.cs', reason: 'unchanged' }],
    };
    const remoteFiles = [remote('b.png', 5, t0)];
    const report = await runSyncPlan(plan, remoteFiles, {
      upload: async () => {},
      download: async () => {},
    });
    expect(report).toEqual({ uploaded: 1, downloaded: 1, skipped: 1, failed: 0, errors: [] });
  });

  it('records a failure without aborting the rest of the plan', async () => {
    const plan: SyncPlan = {
      uploads: [
        { kind: 'upload', name: 'fails.txt', reason: 'only local' },
        { kind: 'upload', name: 'ok.txt', reason: 'only local' },
      ],
      downloads: [],
      skipped: [],
    };
    const uploaded: string[] = [];
    const report = await runSyncPlan(plan, [], {
      upload: async (name) => {
        if (name === 'fails.txt') throw new Error('disk full');
        uploaded.push(name);
      },
      download: async () => {},
    });
    expect(report.uploaded).toBe(1);
    expect(report.failed).toBe(1);
    expect(report.errors).toEqual(['fails.txt: disk full']);
    expect(uploaded).toEqual(['ok.txt']);
  });

  it('ticks progress once per action across uploads and downloads', async () => {
    const plan: SyncPlan = {
      uploads: [{ kind: 'upload', name: 'a.txt', reason: 'only local' }],
      downloads: [{ kind: 'download', name: 'b.png', reason: 'only remote' }],
      skipped: [],
    };
    const remoteFiles = [remote('b.png', 5, t0)];
    const ticks: Array<[number, number]> = [];
    await runSyncPlan(
      plan,
      remoteFiles,
      { upload: async () => {}, download: async () => {} },
      (done, total) => ticks.push([done, total]),
    );
    expect(ticks).toEqual([
      [1, 2],
      [2, 2],
    ]);
  });

  it('counts a missing remote entry as a failure', async () => {
    const plan: SyncPlan = {
      uploads: [],
      downloads: [{ kind: 'download', name: 'gone.txt', reason: 'only remote' }],
      skipped: [],
    };
    const report = await runSyncPlan(plan, [], {
      upload: async () => {},
      download: async () => {},
    });
    expect(report.downloaded).toBe(0);
    expect(report.failed).toBe(1);
    expect(report.errors).toEqual(['gone.txt: remote entry disappeared']);
  });
});

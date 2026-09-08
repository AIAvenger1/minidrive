import { describe, expect, it, vi } from 'vitest';
import { makeFileDto, type SyncLedger } from '@minidrive/shared';
import { BrowserSyncEngine, type DirectoryHandleLike, type FileHandleLike, type LedgerStore } from './browserSync';

function memoryFolder(name: string, files: Record<string, { content: string; lastModified: number }>) {
  const store = new Map(Object.entries(files));
  const handleFor = (fileName: string): FileHandleLike & { createWritable(): Promise<{ write(d: Blob): Promise<void>; close(): Promise<void> }> } => ({
    kind: 'file',
    name: fileName,
    async getFile() {
      const entry = store.get(fileName) ?? { content: '', lastModified: 0 };
      return new File([entry.content], fileName, { lastModified: entry.lastModified });
    },
    async createWritable() {
      let buffered = '';
      return {
        async write(data: Blob) {
          buffered = await data.text();
        },
        async close() {
          store.set(fileName, { content: buffered, lastModified: Date.now() });
        },
      };
    },
  });
  const dir: DirectoryHandleLike = {
    kind: 'directory',
    name,
    async *values() {
      for (const fileName of store.keys()) yield handleFor(fileName);
    },
    async getFileHandle(fileName, options) {
      if (!store.has(fileName) && !options?.create) throw new Error('not found');
      return handleFor(fileName);
    },
  };
  return { dir, store };
}

function memoryLedgers(initial: SyncLedger = {}): LedgerStore & { saved: SyncLedger } {
  const state = { saved: initial } as LedgerStore & { saved: SyncLedger };
  state.load = () => state.saved;
  state.save = (_folder, ledger) => {
    state.saved = ledger;
  };
  return state;
}

describe('BrowserSyncEngine', () => {
  it('uploads local-only files and downloads remote-only files, recording both in the ledger', async () => {
    const { dir, store } = memoryFolder('work', { 'local.cpp': { content: 'int main;', lastModified: 1000 } });
    const remote = makeFileDto({ id: 'r1', name: 'remote.png', size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
    const api = {
      listFiles: vi.fn(async () => [remote]),
      upload: vi.fn(async (name: string) => makeFileDto({ name, updatedAt: '2026-09-08T11:00:00.000Z' })),
      download: vi.fn(async () => new Blob(['png'])),
    };
    const ledgers = memoryLedgers();
    const report = await new BrowserSyncEngine(api, ledgers).synchronize(dir);

    expect(report).toMatchObject({ uploaded: 1, downloaded: 1, skipped: 0, failed: 0 });
    expect(api.upload).toHaveBeenCalledWith('local.cpp', expect.any(File), 'application/octet-stream');
    expect(store.get('remote.png')?.content).toBe('png');
    expect(ledgers.saved['local.cpp']).toMatchObject({ size: 9, mtime: 1000, updatedAt: '2026-09-08T11:00:00.000Z' });
    expect(ledgers.saved['remote.png']).toMatchObject({ size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
  });

  it('skips a file the ledger already knows, even though the browser could not set its mtime', async () => {
    const { dir } = memoryFolder('work', { 'same.cpp': { content: 'abc', lastModified: 5000 } });
    const remote = makeFileDto({ id: 'r1', name: 'same.cpp', size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
    const api = { listFiles: vi.fn(async () => [remote]), upload: vi.fn(), download: vi.fn() };
    const ledgers = memoryLedgers({ 'same.cpp': { size: 3, mtime: 5000, updatedAt: '2026-09-08T10:00:00.000Z' } });
    const report = await new BrowserSyncEngine(api, ledgers).synchronize(dir);

    expect(report).toMatchObject({ uploaded: 0, downloaded: 0, skipped: 1, failed: 0 });
    expect(api.upload).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
  });

  it('counts a failed transfer without aborting the rest and reports progress', async () => {
    const { dir } = memoryFolder('work', { 'a.cpp': { content: 'a', lastModified: 1 }, 'b.cpp': { content: 'b', lastModified: 1 } });
    const api = {
      listFiles: vi.fn(async () => []),
      upload: vi.fn(async (name: string) => {
        if (name === 'a.cpp') throw new Error('boom');
        return makeFileDto({ name });
      }),
      download: vi.fn(),
    };
    const progress: Array<[number, number]> = [];
    const report = await new BrowserSyncEngine(api, memoryLedgers()).synchronize(dir, (done, total) => progress.push([done, total]));

    expect(report).toMatchObject({ uploaded: 1, failed: 1 });
    expect(report.errors).toEqual(['a.cpp: boom']);
    expect(progress).toEqual([[1, 2], [2, 2]]);
  });

  it('ignores dot-prefixed and non-file entries when scanning', async () => {
    const { dir } = memoryFolder('work', { '.hidden': { content: 'x', lastModified: 1 }, 'ok.png': { content: 'y', lastModified: 1 } });
    const files = await new BrowserSyncEngine({ listFiles: vi.fn(), upload: vi.fn(), download: vi.fn() }, memoryLedgers()).scan(dir);
    expect(files.map((f) => f.name)).toEqual(['ok.png']);
  });
});

import { mkdtemp, readFile, stat, utimes, writeFile } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import { describe, expect, it } from 'vitest';
import type { FileDto } from '@minidrive/shared';
import { SyncEngine } from './syncEngine';

const remoteFile = (name: string, body: string, updatedAt: string): FileDto & { body: string } => ({
  id: `r-${name}`, name, extension: '', size: Buffer.byteLength(body), createdAt: updatedAt, updatedAt, uploadedBy: 'olena', modifiedBy: 'olena', body,
});

function fakeApi(remote: (FileDto & { body: string })[]) {
  const uploads: string[] = [];
  return {
    uploads,
    listFiles: async () => remote.map(({ body, ...dto }) => dto),
    upload: async (name: string) => {
      uploads.push(name);
      return remote[0] ?? remoteFile(name, '', new Date().toISOString());
    },
    download: async (id: string) => new Blob([remote.find((r) => r.id === id)!.body]),
  };
}

describe('SyncEngine', () => {
  it('uploads local-only files, downloads remote-only files and sets mtime', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'local.txt'), 'hello');
    const remoteUpdated = '2026-09-01T10:00:00.000Z';
    const api = fakeApi([remoteFile('remote.cs', 'class R {}', remoteUpdated)]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(api.uploads).toEqual(['local.txt']);
    expect(await readFile(join(dir, 'remote.cs'), 'utf8')).toBe('class R {}');
    expect(Math.abs((await stat(join(dir, 'remote.cs'))).mtimeMs - Date.parse(remoteUpdated))).toBeLessThan(1000);
    expect(report).toMatchObject({ uploaded: 1, downloaded: 1, skipped: 0, failed: 0 });
  });

  it('skips a file that is identical on both sides', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    const updatedAt = '2026-09-01T10:00:00.000Z';
    await writeFile(join(dir, 'same.cpp'), 'int main(){}');
    await utimes(join(dir, 'same.cpp'), new Date(updatedAt), new Date(updatedAt));
    const api = fakeApi([remoteFile('same.cpp', 'int main(){}', updatedAt)]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report).toMatchObject({ uploaded: 0, downloaded: 0, skipped: 1 });
  });

  it('counts failures instead of aborting', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'a.txt'), 'a');
    const api = fakeApi([]);
    api.upload = async () => { throw new Error('network'); };
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('a.txt');
  });
});

import { mkdtemp, readdir, readFile, stat, utimes, writeFile } from 'fs/promises';
import { tmpdir } from 'os';
import { dirname, join } from 'path';
import { describe, expect, it } from 'vitest';
import { makeFileDto, type FileDto } from '@minidrive/shared';
import { SyncEngine } from './syncEngine';

function remoteFile(name: string, body: string, updatedAt: string): FileDto & { body: string } {
  return {
    ...makeFileDto({ id: `r-${name}`, name, extension: '', size: Buffer.byteLength(body), createdAt: updatedAt, updatedAt, uploadedBy: 'olena', modifiedBy: 'olena' }),
    body,
  };
}

function fakeApi(remote: (FileDto & { body: string })[], uploadResults: Record<string, FileDto> = {}) {
  const uploads: string[] = [];
  return {
    uploads,
    listFiles: async () => remote.map(({ body, ...dto }) => dto),
    async upload(name: string) {
      uploads.push(name);
      return uploadResults[name] ?? makeFileDto({ id: `u-${name}`, name, updatedAt: new Date().toISOString() });
    },
    async download(id: string) {
      return new Blob([remote.find((r) => r.id === id)!.body]);
    },
  };
}

describe('SyncEngine', () => {
  it('uploads local-only files, downloads remote-only files and sets mtime', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'local.txt'), 'hello');
    const remoteUpdated = '2026-09-01T10:00:00.000Z';
    const uploadedAt = '2026-09-02T12:00:00.000Z';
    const api = fakeApi([remoteFile('remote.cs', 'class R {}', remoteUpdated)], {
      'local.txt': makeFileDto({ id: 'u-local.txt', name: 'local.txt', updatedAt: uploadedAt }),
    });
    const report = await new SyncEngine(api).synchronize(dir);
    expect(api.uploads).toEqual(['local.txt']);
    expect(await readFile(join(dir, 'remote.cs'), 'utf8')).toBe('class R {}');
    expect(Math.abs((await stat(join(dir, 'remote.cs'))).mtimeMs - Date.parse(remoteUpdated))).toBeLessThan(1000);
    expect(Math.abs((await stat(join(dir, 'local.txt'))).mtimeMs - Date.parse(uploadedAt))).toBeLessThan(1000);
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
    api.upload = async () => {
      throw new Error('network');
    };
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('a.txt');
  });

  it('refuses to write a remote file whose name escapes the target directory', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    const api = fakeApi([remoteFile('../escape.txt', 'evil', new Date().toISOString())]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('unsafe file name');
    expect(await readdir(dirname(dir))).not.toContain('escape.txt');
  });

  it('refuses to write a remote file whose name carries a backslash', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    const api = fakeApi([remoteFile('a\\b.cs', 'evil', new Date().toISOString())]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('unsafe file name');
    expect(await readdir(dir)).toEqual([]);
  });

  it('refuses to download a dot-prefixed remote file instead of re-downloading it forever', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    const api = fakeApi([remoteFile('.env', 'SECRET=1', new Date().toISOString())]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('unsafe file name');
    expect(await readdir(dir)).toEqual([]);
  });

  it('reports progress as each upload and download completes', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'local.txt'), 'hello');
    const api = fakeApi([remoteFile('remote.cs', 'class R {}', new Date().toISOString())]);
    const calls: Array<{ done: number; total: number }> = [];
    await new SyncEngine(api).synchronize(dir, (done, total) => calls.push({ done, total }));
    expect(calls).toHaveLength(2);
    expect(calls.every((c) => c.total === 2)).toBe(true);
    expect(calls.map((c) => c.done)).toEqual([1, 2]);
  });
});

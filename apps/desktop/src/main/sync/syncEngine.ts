import { readFile, utimes, writeFile } from 'fs/promises';
import { join } from 'path';
import { computeSyncPlan, type ApiClient, type FileDto, type LocalFileInfo, type SyncReport } from '@minidrive/shared';
import { LocalFolderScanner } from './localFolderScanner';

export type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>;
type Progress = (done: number, total: number) => void;

export class SyncEngine {
  constructor(private readonly api: SyncApi, private readonly scanner = LocalFolderScanner) {}

  scan(dir: string): Promise<LocalFileInfo[]> {
    return this.scanner.scan(dir);
  }

  async synchronize(dir: string, onProgress?: Progress): Promise<SyncReport> {
    const [local, remote] = await Promise.all([this.scan(dir), this.api.listFiles()]);
    const plan = computeSyncPlan(local, remote);
    const remoteByName = new Map(remote.map((r) => [r.name, r]));
    const report: SyncReport = { uploaded: 0, downloaded: 0, skipped: plan.skipped.length, failed: 0, errors: [] };
    const total = plan.uploads.length + plan.downloads.length;
    let done = 0;

    for (const action of plan.uploads) {
      try {
        await this.api.upload(action.name, await readFile(join(dir, action.name)));
        report.uploaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    for (const action of plan.downloads) {
      try {
        await this.downloadTo(dir, remoteByName.get(action.name)!);
        report.downloaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }
    return report;
  }

  private async downloadTo(dir: string, file: FileDto): Promise<void> {
    const blob = await this.api.download(file.id);
    const target = join(dir, file.name);
    await writeFile(target, Buffer.from(await blob.arrayBuffer()));
    const t = new Date(file.updatedAt);
    await utimes(target, t, t);
  }
}

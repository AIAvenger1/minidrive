import { readFile, utimes, writeFile } from 'fs/promises';
import { join } from 'path';
import {
  computeSyncPlan,
  isSyncableName,
  runSyncPlan,
  type FileDto,
  type LocalFileInfo,
  type SyncApi,
  type SyncProgress,
  type SyncReport,
} from '@minidrive/shared';
import { LocalFolderScanner } from './localFolderScanner';

export class SyncEngine {
  constructor(private readonly api: SyncApi, private readonly scanner = LocalFolderScanner) {}

  scan(dir: string): Promise<LocalFileInfo[]> {
    return this.scanner.scan(dir);
  }

  async synchronize(dir: string, onProgress?: SyncProgress): Promise<SyncReport> {
    const [local, remote] = await Promise.all([this.scan(dir), this.api.listFiles()]);
    const plan = computeSyncPlan(local, remote);
    return runSyncPlan(
      plan,
      remote,
      {
        upload: (name) => this.uploadFrom(dir, name),
        download: (file) => this.downloadTo(dir, file),
      },
      onProgress,
    );
  }

  private async uploadFrom(dir: string, name: string): Promise<void> {
    if (!isSyncableName(name)) throw new Error('unsafe file name');
    const dto = await this.api.upload(name, await readFile(join(dir, name)));
    const t = new Date(dto.updatedAt);
    await utimes(join(dir, name), t, t);
  }

  private async downloadTo(dir: string, file: FileDto): Promise<void> {
    if (!isSyncableName(file.name)) throw new Error('unsafe file name');
    const blob = await this.api.download(file.id);
    const target = join(dir, file.name);
    await writeFile(target, Buffer.from(await blob.arrayBuffer()));
    const t = new Date(file.updatedAt);
    await utimes(target, t, t);
  }
}

import {
  computeSyncPlan,
  emptySyncReport,
  isSyncableName,
  pruneLedger,
  reconcileWithLedger,
  recordTransfer,
  type ApiClient,
  type FileDto,
  type LocalFileInfo,
  type SyncLedger,
  type SyncLedgerEntry,
  type SyncReport,
} from '@minidrive/shared';

export type WritableLike = { write(data: Blob): Promise<void>; close(): Promise<void> };
export type FileHandleLike = { kind: 'file'; name: string; getFile(): Promise<File> };
export type WritableFileHandleLike = FileHandleLike & { createWritable(): Promise<WritableLike> };
export type DirectoryHandleLike = {
  kind: 'directory';
  name: string;
  values(): AsyncIterable<FileHandleLike | DirectoryHandleLike>;
  getFileHandle(name: string, options?: { create?: boolean }): Promise<WritableFileHandleLike>;
};
export type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>;
export type LedgerStore = { load(folder: string): SyncLedger; save(folder: string, ledger: SyncLedger): void };
type Progress = (done: number, total: number) => void;
type PickerWindow = { showDirectoryPicker(options: { mode: 'readwrite' }): Promise<DirectoryHandleLike> };

export function supportsFolderSync(): boolean {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

export function pickFolder(): Promise<DirectoryHandleLike> {
  return (window as unknown as PickerWindow).showDirectoryPicker({ mode: 'readwrite' });
}

export class BrowserSyncEngine {
  constructor(private readonly api: SyncApi, private readonly ledgers: LedgerStore) {}

  async scan(dir: DirectoryHandleLike): Promise<LocalFileInfo[]> {
    const files: LocalFileInfo[] = [];
    for await (const handle of dir.values()) {
      if (handle.kind !== 'file' || !isSyncableName(handle.name)) continue;
      const file = await handle.getFile();
      files.push({ name: handle.name, size: file.size, mtime: file.lastModified });
    }
    return files;
  }

  async synchronize(dir: DirectoryHandleLike, onProgress?: Progress): Promise<SyncReport> {
    const [scanned, remote] = await Promise.all([this.scan(dir), this.api.listFiles()]);
    let ledger = pruneLedger(this.ledgers.load(dir.name), scanned);
    const plan = computeSyncPlan(reconcileWithLedger(scanned, ledger), remote);
    const remoteByName = new Map(remote.map((r) => [r.name, r]));
    const report = emptySyncReport();
    report.skipped = plan.skipped.length;
    const total = plan.uploads.length + plan.downloads.length;
    let done = 0;

    for (const action of plan.uploads) {
      try {
        ledger = recordTransfer(ledger, action.name, await this.uploadFrom(dir, action.name));
        report.uploaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    for (const action of plan.downloads) {
      try {
        const dto = remoteByName.get(action.name);
        if (!dto) throw new Error('remote entry disappeared');
        ledger = recordTransfer(ledger, action.name, await this.downloadTo(dir, dto));
        report.downloaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    this.ledgers.save(dir.name, ledger);
    return report;
  }

  private async uploadFrom(dir: DirectoryHandleLike, name: string): Promise<SyncLedgerEntry> {
    const file = await (await dir.getFileHandle(name)).getFile();
    const dto = await this.api.upload(name, file, file.type || 'application/octet-stream');
    return { size: file.size, mtime: file.lastModified, updatedAt: dto.updatedAt };
  }

  private async downloadTo(dir: DirectoryHandleLike, file: FileDto): Promise<SyncLedgerEntry> {
    const blob = await this.api.download(file.id);
    const handle = await dir.getFileHandle(file.name, { create: true });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    const written = await handle.getFile();
    return { size: written.size, mtime: written.lastModified, updatedAt: file.updatedAt };
  }
}

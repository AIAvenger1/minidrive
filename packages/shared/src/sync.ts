import type { FileDto, LocalFileInfo, SyncAction, SyncPlan, SyncReport } from './types';
import type { ApiClient } from './apiClient';

export const SKEW_MS = 2000;

export type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>;
export type SyncProgress = (done: number, total: number) => void;
export type SyncTransfers = {
  upload(name: string): Promise<void>;
  download(file: FileDto): Promise<void>;
};

export function computeSyncPlan(local: LocalFileInfo[], remote: FileDto[]): SyncPlan {
  const plan: SyncPlan = { uploads: [], downloads: [], skipped: [] };
  const remoteByName = new Map(remote.map((r) => [r.name, r]));
  const localByName = new Map(local.map((l) => [l.name, l]));

  for (const l of local) {
    const r = remoteByName.get(l.name);
    if (!r) {
      plan.uploads.push(action('upload', l.name, 'only local'));
      continue;
    }
    const remoteTime = Date.parse(r.updatedAt);
    if (Number.isNaN(remoteTime)) {
      plan.downloads.push(action('download', l.name, 'invalid remote timestamp'));
      continue;
    }
    const sameSize = l.size === r.size;
    const closeInTime = Math.abs(l.mtime - remoteTime) <= SKEW_MS;
    if (sameSize && closeInTime) {
      plan.skipped.push(action('skip', l.name, 'unchanged'));
    } else if (l.mtime >= remoteTime) {
      plan.uploads.push(action('upload', l.name, 'local newer'));
    } else {
      plan.downloads.push(action('download', l.name, 'remote newer'));
    }
  }

  for (const r of remote) {
    if (!localByName.has(r.name)) {
      plan.downloads.push(action('download', r.name, 'only remote'));
    }
  }
  return plan;
}

function action(kind: SyncAction['kind'], name: string, reason: string): SyncAction {
  return { kind, name, reason };
}

export function emptySyncReport(): SyncReport {
  return { uploaded: 0, downloaded: 0, skipped: 0, failed: 0, errors: [] };
}

export function failedSyncReport(message: string): SyncReport {
  return { uploaded: 0, downloaded: 0, skipped: 0, failed: 1, errors: [message] };
}

export async function runSyncPlan(
  plan: SyncPlan,
  remote: FileDto[],
  transfers: SyncTransfers,
  onProgress?: SyncProgress,
): Promise<SyncReport> {
  const remoteByName = new Map(remote.map((r) => [r.name, r]));
  const report = emptySyncReport();
  report.skipped = plan.skipped.length;
  const total = plan.uploads.length + plan.downloads.length;
  let done = 0;

  for (const action of plan.uploads) {
    try {
      await transfers.upload(action.name);
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
      await transfers.download(dto);
      report.downloaded += 1;
    } catch (err) {
      report.failed += 1;
      report.errors.push(`${action.name}: ${(err as Error).message}`);
    }
    onProgress?.(++done, total);
  }

  return report;
}

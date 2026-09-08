import type { FileDto, LocalFileInfo, SyncAction, SyncPlan } from './types';

export const SKEW_MS = 2000;

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

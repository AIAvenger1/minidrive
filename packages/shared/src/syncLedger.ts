import type { LocalFileInfo } from './types';

export type SyncLedgerEntry = { size: number; mtime: number; updatedAt: string };
export type SyncLedger = Record<string, SyncLedgerEntry>;

export function reconcileWithLedger(local: LocalFileInfo[], ledger: SyncLedger): LocalFileInfo[] {
  return local.map((file) => {
    const entry = ledger[file.name];
    if (!entry || entry.size !== file.size || entry.mtime !== file.mtime) return { ...file };
    return { ...file, mtime: Date.parse(entry.updatedAt) };
  });
}

export function recordTransfer(ledger: SyncLedger, name: string, entry: SyncLedgerEntry): SyncLedger {
  return { ...ledger, [name]: entry };
}

export function pruneLedger(ledger: SyncLedger, present: LocalFileInfo[]): SyncLedger {
  const names = new Set(present.map((file) => file.name));
  return Object.fromEntries(Object.entries(ledger).filter(([name]) => names.has(name)));
}

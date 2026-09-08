import type { SyncLedger } from '@minidrive/shared';
import type { LedgerStore } from './browserSync';

const PREFIX = 'minidrive.sync.';

export const localLedgerStore: LedgerStore = {
  load(folder) {
    try {
      return JSON.parse(window.localStorage.getItem(PREFIX + folder) ?? '{}') as SyncLedger;
    } catch {
      return {};
    }
  },
  save(folder, ledger) {
    window.localStorage.setItem(PREFIX + folder, JSON.stringify(ledger));
  },
};

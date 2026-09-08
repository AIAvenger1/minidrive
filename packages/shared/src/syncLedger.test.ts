import { describe, expect, it } from 'vitest';
import { pruneLedger, reconcileWithLedger, recordTransfer, type SyncLedger } from './syncLedger';

const updatedAt = '2026-09-08T10:00:00.000Z';

describe('reconcileWithLedger', () => {
  it('replaces mtime with the recorded updatedAt when size and mtime match the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 10, mtime: 5000 }], ledger);
    expect(out).toEqual([{ name: 'a.cpp', size: 10, mtime: Date.parse(updatedAt) }]);
  });

  it('leaves a file alone when its size differs from the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 11, mtime: 5000 }], ledger);
    expect(out[0].mtime).toBe(5000);
  });

  it('leaves a file alone when its mtime differs from the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 10, mtime: 6000 }], ledger);
    expect(out[0].mtime).toBe(6000);
  });

  it('leaves files without a ledger entry alone and does not mutate the input', () => {
    const input = [{ name: 'b.png', size: 3, mtime: 1 }];
    const out = reconcileWithLedger(input, {});
    expect(out).toEqual(input);
    expect(out).not.toBe(input);
  });
});

describe('recordTransfer', () => {
  it('returns a new ledger with the entry added and keeps the old one untouched', () => {
    const before: SyncLedger = {};
    const after = recordTransfer(before, 'a.cpp', { size: 1, mtime: 2, updatedAt });
    expect(after['a.cpp']).toEqual({ size: 1, mtime: 2, updatedAt });
    expect(before).toEqual({});
  });
});

describe('pruneLedger', () => {
  it('drops entries whose file is no longer present', () => {
    const ledger: SyncLedger = {
      'a.cpp': { size: 1, mtime: 2, updatedAt },
      'gone.txt': { size: 1, mtime: 2, updatedAt },
    };
    expect(Object.keys(pruneLedger(ledger, [{ name: 'a.cpp', size: 1, mtime: 2 }]))).toEqual(['a.cpp']);
  });
});

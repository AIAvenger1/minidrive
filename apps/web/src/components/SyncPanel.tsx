'use client';

import { useRef, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { getApi, SyncPanel as SharedSyncPanel } from '@minidrive/ui';
import { BrowserSyncEngine, pickFolder as pickFolderHandle, supportsFolderSync, type DirectoryHandleLike } from '../lib/browserSync';
import { localLedgerStore } from '../lib/syncLedgerStore';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const supported = supportsFolderSync();
  const [folder, setFolder] = useState<DirectoryHandleLike | null>(null);
  const folderRef = useRef<DirectoryHandleLike | null>(null);

  async function pickFolder(): Promise<string | null> {
    const chosen = await pickFolderHandle();
    folderRef.current = chosen;
    setFolder(chosen);
    return chosen.name;
  }

  async function runSync(onProgress: (done: number, total: number) => void): Promise<SyncReport> {
    const dir = folderRef.current;
    if (!dir) throw new Error('folder not selected');
    return new BrowserSyncEngine(getApi(), localLedgerStore).synchronize(dir, onProgress);
  }

  return (
    <SharedSyncPanel
      folderName={folder?.name ?? null}
      pickFolder={pickFolder}
      runSync={runSync}
      onSynced={onSynced}
      unsupportedMessage={supported ? undefined : 'Синхронізація папки недоступна в цьому браузері. Потрібен Chrome або Edge.'}
    />
  );
}

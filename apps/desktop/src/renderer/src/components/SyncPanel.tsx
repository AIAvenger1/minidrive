import { useEffect, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { Checkbox, Label, SyncPanel as SharedSyncPanel } from '@minidrive/ui';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const [folder, setFolder] = useState<string | null>(null);
  const [autoWatch, setAutoWatch] = useState(false);
  const [externalReport, setExternalReport] = useState<SyncReport | null>(null);
  const [externalError, setExternalError] = useState<string | null>(null);

  useEffect(() => {
    window.minidrive.sync
      .status()
      .then((s) => {
        setFolder(s.boundFolder);
        setAutoWatch(s.autoWatch);
      })
      .catch((err) => setExternalError((err as Error).message));
    const offAuto = window.minidrive.sync.onAutoSync((r) => {
      setExternalReport(r);
      onSynced();
    });
    return () => {
      offAuto();
    };
  }, [onSynced]);

  async function pickFolder(): Promise<string | null> {
    const chosen = await window.minidrive.folder.pick();
    if (chosen) setFolder(chosen);
    return chosen;
  }

  async function runSync(onProgress: (done: number, total: number) => void): Promise<SyncReport> {
    const off = window.minidrive.sync.onProgress((p) => onProgress(p.done, p.total));
    try {
      return await window.minidrive.sync.run();
    } finally {
      off();
    }
  }

  async function toggleWatch(enabled: boolean) {
    try {
      setAutoWatch(await window.minidrive.sync.watch(enabled));
    } catch (err) {
      setAutoWatch(!enabled);
      setExternalError((err as Error).message);
    }
  }

  return (
    <SharedSyncPanel
      folderName={folder}
      pickFolder={pickFolder}
      runSync={runSync}
      onSynced={onSynced}
      externalReport={externalReport}
      externalError={externalError}
      extraControls={
        <div className="flex items-center gap-2">
          <Checkbox id="auto-watch" checked={autoWatch} disabled={!folder} onCheckedChange={(v) => toggleWatch(Boolean(v))} />
          <Label htmlFor="auto-watch">Автоматично відстежувати зміни</Label>
        </div>
      }
    />
  );
}

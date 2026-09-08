'use client';

import { useMemo, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { Alert, AlertDescription, Button, Card, CardContent, Progress, getApi } from '@minidrive/ui';
import { BrowserSyncEngine, pickFolder, supportsFolderSync, type DirectoryHandleLike } from '../lib/browserSync';
import { localLedgerStore } from '../lib/syncLedgerStore';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const supported = useMemo(() => supportsFolderSync(), []);
  const [folder, setFolder] = useState<DirectoryHandleLike | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(): Promise<DirectoryHandleLike | null> {
    try {
      const chosen = await pickFolder();
      setFolder(chosen);
      setReport(null);
      return chosen;
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setError((err as Error).message);
      return null;
    }
  }

  async function sync() {
    const dir = folder ?? (await choose());
    if (!dir) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      const result = await new BrowserSyncEngine(getApi(), localLedgerStore).synchronize(dir, (done, total) =>
        setProgress({ done, total }),
      );
      setReport(result);
      onSynced();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!supported) {
    return (
      <Alert>
        <AlertDescription>Синхронізація папки недоступна в цьому браузері. Потрібен Chrome або Edge.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-3 pt-6">
        <span className="text-sm text-muted-foreground">{folder ? `Папка: ${folder.name}` : 'Папку не обрано'}</span>
        <Button type="button" variant="outline" onClick={choose} disabled={busy}>
          Обрати папку
        </Button>
        <Button type="button" onClick={sync} disabled={busy}>
          Синхронізувати
        </Button>
        {progress && progress.total > 0 && (
          <Progress className="w-40" value={(progress.done / progress.total) * 100} />
        )}
        {report && (
          <Alert className="w-full">
            <AlertDescription>
              Завантажено {report.uploaded}, вивантажено {report.downloaded}, пропущено {report.skipped}, помилок{' '}
              {report.failed}
              {report.errors.length > 0 && <span> — {report.errors.join('; ')}</span>}
            </AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" className="w-full">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

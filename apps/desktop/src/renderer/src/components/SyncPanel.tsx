import { useEffect, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { Alert, AlertDescription, Button, Card, CardContent, Checkbox, Label, Progress } from '@minidrive/ui';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const [folder, setFolder] = useState<string | null>(null);
  const [autoWatch, setAutoWatch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.minidrive.sync
      .status()
      .then((s) => {
        setFolder(s.boundFolder);
        setAutoWatch(s.autoWatch);
      })
      .catch((err) => setError((err as Error).message));
    const offProgress = window.minidrive.sync.onProgress(setProgress);
    const offAuto = window.minidrive.sync.onAutoSync((r) => {
      setReport(r);
      onSynced();
    });
    return () => {
      offProgress();
      offAuto();
    };
  }, [onSynced]);

  async function pick() {
    try {
      const chosen = await window.minidrive.folder.pick();
      if (chosen) setFolder(chosen);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function sync() {
    let dir = folder;
    if (!dir) {
      try {
        dir = await window.minidrive.folder.pick();
      } catch (err) {
        setError((err as Error).message);
        return;
      }
      if (!dir) return;
      setFolder(dir);
    }
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      setReport(await window.minidrive.sync.run());
      onSynced();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleWatch(enabled: boolean) {
    try {
      setAutoWatch(await window.minidrive.sync.watch(enabled));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Card className="sync">
      <CardContent className="grid gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="truncate font-mono text-xs">{folder ?? "Папку не прив'язано"}</span>
          <Button type="button" variant="outline" size="sm" onClick={pick}>
            {folder ? 'Змінити' : "Прив'язати папку"}
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" onClick={sync} disabled={busy}>
            Синхронізувати
          </Button>
          <div className="flex items-center gap-2">
            <Checkbox id="auto-watch" checked={autoWatch} disabled={!folder} onCheckedChange={(v) => toggleWatch(Boolean(v))} />
            <Label htmlFor="auto-watch">Автоматично відстежувати зміни</Label>
          </div>
        </div>
        {busy && progress && (
          <div className="grid gap-1">
            <span className="text-xs text-muted-foreground">
              Передано {progress.done} з {progress.total}
            </span>
            <Progress value={(progress.done / Math.max(progress.total, 1)) * 100} />
          </div>
        )}
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {report && (
          <Alert>
            <AlertDescription>
              Завантажено {report.uploaded}, вивантажено {report.downloaded}, пропущено {report.skipped}, помилок{' '}
              {report.failed}
              {report.errors.length > 0 && <span> — {report.errors.join('; ')}</span>}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

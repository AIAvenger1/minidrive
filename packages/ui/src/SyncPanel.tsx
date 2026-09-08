import { useEffect, useState, type ReactNode } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { Alert, AlertDescription } from './components/ui/alert';
import { Button } from './components/ui/button';
import { Card, CardContent } from './components/ui/card';
import { Progress } from './components/ui/progress';
import { SyncReportSummary } from './SyncReportSummary';

export type SyncPanelProps = {
  folderName: string | null;
  pickFolder: () => Promise<string | null>;
  runSync: (onProgress: (done: number, total: number) => void) => Promise<SyncReport>;
  onSynced: () => void;
  extraControls?: ReactNode;
  unsupportedMessage?: string;
  externalReport?: SyncReport | null;
  externalError?: string | null;
};

export function SyncPanel({
  folderName,
  pickFolder,
  runSync,
  onSynced,
  extraControls,
  unsupportedMessage,
  externalReport,
  externalError,
}: SyncPanelProps) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (externalReport) setReport(externalReport);
  }, [externalReport]);

  useEffect(() => {
    if (externalError) setError(externalError);
  }, [externalError]);

  if (unsupportedMessage) {
    return (
      <Alert>
        <AlertDescription>{unsupportedMessage}</AlertDescription>
      </Alert>
    );
  }

  async function handlePick() {
    try {
      await pickFolder();
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setError((err as Error).message);
    }
  }

  async function handleSync() {
    let name = folderName;
    if (!name) {
      try {
        name = await pickFolder();
      } catch (err) {
        if ((err as Error).name !== 'AbortError') setError((err as Error).message);
        return;
      }
      if (!name) return;
    }
    setBusy(true);
    setError(null);
    setProgress({ done: 0, total: 0 });
    try {
      const result = await runSync((done, total) => setProgress({ done, total }));
      setReport(result);
      onSynced();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-3 pt-6">
        <span className="text-sm text-muted-foreground">{folderName ? `Папка: ${folderName}` : 'Папку не обрано'}</span>
        <Button type="button" variant="outline" onClick={handlePick} disabled={busy}>
          Обрати папку
        </Button>
        {extraControls}
        <Button type="button" onClick={handleSync} disabled={busy}>
          Синхронізувати
        </Button>
        {progress.total > 0 && <Progress className="w-40" value={(progress.done / progress.total) * 100} />}
        {report && <SyncReportSummary report={report} />}
        {(error || (report && report.errors.length > 0)) && (
          <Alert variant="destructive" className="w-full">
            <AlertDescription>
              {error && <div>{error}</div>}
              {report?.errors.map((line) => <div key={line}>{line}</div>)}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

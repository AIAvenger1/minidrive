import { useEffect, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const [folder, setFolder] = useState<string | null>(null);
  const [autoWatch, setAutoWatch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.minidrive.sync.status().then((s) => {
      setFolder(s.boundFolder);
      setAutoWatch(s.autoWatch);
    });
    const offProgress = window.minidrive.sync.onProgress(setProgress);
    const offAuto = window.minidrive.sync.onAutoSync((r) => {
      setReport(r as SyncReport);
      onSynced();
    });
    return () => {
      offProgress();
      offAuto();
    };
  }, [onSynced]);

  async function pick() {
    const chosen = await window.minidrive.folder.pick();
    if (chosen) setFolder(chosen);
  }

  async function sync() {
    if (!folder) return pick();
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
    setAutoWatch(await window.minidrive.sync.watch(enabled));
  }

  return (
    <section className="sync">
      <div className="folder">
        <span>{folder ?? "Папку не прив'язано"}</span>
        <button type="button" onClick={pick}>{folder ? 'Змінити' : "Прив'язати папку"}</button>
      </div>
      <div className="actions">
        <button type="button" onClick={sync} disabled={busy}>Синхронізувати</button>
        <label>
          <input type="checkbox" checked={autoWatch} disabled={!folder} onChange={(e) => toggleWatch(e.target.checked)} />
          Автоматично відстежувати зміни
        </label>
      </div>
      {busy && progress && <p>Передано {progress.done} з {progress.total}</p>}
      {error && <p className="error">{error}</p>}
      {report && (
        <p className="report">
          Завантажено {report.uploaded}, вивантажено {report.downloaded}, пропущено {report.skipped}, помилок {report.failed}
          {report.errors.length > 0 && <span> — {report.errors.join('; ')}</span>}
        </p>
      )}
    </section>
  );
}

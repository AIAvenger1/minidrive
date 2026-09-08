import { useCallback, useEffect, useState, type DragEvent, type ReactNode } from 'react';
import { MAX_UPLOAD_MB, splitBySize, type ApiClient, type FileDto, type UserDto } from '@minidrive/shared';
import { ColumnToggle } from './ColumnToggle';
import { FileTable } from './FileTable';
import { FilterControl } from './FilterControl';
import { PreviewPanel } from './PreviewPanel';
import { SortControl } from './SortControl';
import { UploadDropzone } from './UploadDropzone';
import { useDrive } from './useDrive';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './components/ui/dialog';

type Props = {
  user: UserDto;
  api: ApiClient;
  onLogout: () => void;
  saveFile: (file: FileDto, blob: Blob) => Promise<void> | void;
  onRowDragStart?: (file: FileDto, e: DragEvent) => void;
  subscribeErrors?: (report: (message: string) => void) => () => void;
  renderSyncPanel?: (onSynced: () => void) => ReactNode;
};

export function DriveWorkspace({ user, api, onLogout, saveFile, onRowDragStart, subscribeErrors, renderSyncPanel }: Props) {
  const { vm, refresh, update, busy, error, setError } = useDrive(api, onLogout);
  const [working, setWorking] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => subscribeErrors?.(setError), [subscribeErrors, setError]);

  const loadContent = useCallback((f: FileDto) => api.download(f.id), [api]);

  async function run(action: () => Promise<void>) {
    setWorking(true);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorking(false);
    }
  }

  function uploadFiles(files: File[]) {
    const { accepted, rejected } = splitBySize(files);
    return run(async () => {
      for (const f of accepted) await api.upload(f.name, f, f.type || 'application/octet-stream');
      if (accepted.length > 0) await refresh();
      if (rejected.length > 0) {
        throw new Error(`Завеликі файли (понад ${MAX_UPLOAD_MB} МБ): ${rejected.map((f) => f.name).join(', ')}`);
      }
    });
  }

  function downloadSelected() {
    const file = vm.selected;
    if (!file) return;
    return run(async () => {
      await saveFile(file, await api.download(file.id));
    });
  }

  function deleteSelected() {
    const file = vm.selected;
    if (!file) return;
    setConfirmDelete(false);
    return run(async () => {
      await api.remove(file.id);
      await refresh();
    });
  }

  return (
    <div className="drive">
      <header className="flex items-center gap-4">
        <strong>MiniDrive</strong>
        <Badge variant="secondary" className="ml-auto">
          {user.username}
        </Badge>
        <Button type="button" variant="ghost" onClick={onLogout}>
          Вийти
        </Button>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <SortControl order={vm.order} onChange={(o) => update((m) => m.setOrder(o))} />
        <FilterControl filter={vm.filter} onChange={(f) => update((m) => m.setFilter(f))} />
        <ColumnToggle columns={vm.columns} onToggle={(k) => update((m) => m.toggleColumn(k))} />
        <Button type="button" variant="outline" onClick={refresh} disabled={busy}>
          Оновити
        </Button>
        <Button type="button" variant="outline" onClick={downloadSelected} disabled={!vm.selected || working}>
          Скачати
        </Button>
        <Button type="button" variant="destructive" onClick={() => setConfirmDelete(true)} disabled={!vm.selected || working}>
          Видалити
        </Button>
      </div>
      {error && <p className="text-destructive">{error}</p>}
      {renderSyncPanel?.(refresh)}
      <div className="drive-body">
        <UploadDropzone onFiles={uploadFiles} busy={working}>
          <FileTable
            files={vm.visibleFiles}
            columns={vm.columns}
            selected={vm.selected}
            onSelect={(f) => update((m) => m.select(f))}
            onDragStart={onRowDragStart}
          />
        </UploadDropzone>
        <PreviewPanel file={vm.selected} loadContent={loadContent} />
      </div>
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Видалити файл?</DialogTitle>
            <DialogDescription>Файл буде видалено без можливості відновлення.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirmDelete(false)}>
              Скасувати
            </Button>
            <Button type="button" variant="destructive" onClick={deleteSelected}>
              Видалити
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

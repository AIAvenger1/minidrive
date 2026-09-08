import { useCallback, useEffect, useState } from 'react';
import type { FileDto, UserDto } from '@minidrive/shared';
import {
  Badge,
  Button,
  ColumnToggle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  FileTable,
  FilterControl,
  getApi,
  PreviewPanel,
  SortControl,
  UploadDropzone,
  useDrive
} from '@minidrive/ui';
import { SyncPanel } from '../components/SyncPanel';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const { vm, refresh, update, busy, error, setError } = useDrive(getApi(), onLogout);
  const [working, setWorking] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const unsubscribe = window.minidrive.file.onDragOutError((message) => setError(message));
    return () => {
      unsubscribe();
    };
  }, [setError]);

  const loadContent = useCallback((f: FileDto) => getApi().download(f.id), []);

  async function uploadFiles(files: File[]) {
    setWorking(true);
    try {
      for (const f of files) await getApi().upload(f.name, f, f.type || 'application/octet-stream');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorking(false);
    }
  }

  async function downloadSelected() {
    if (!vm.selected) return;
    setWorking(true);
    try {
      const blob = await getApi().download(vm.selected.id);
      await window.minidrive.file.saveAs(vm.selected.name, await blob.arrayBuffer());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorking(false);
    }
  }

  async function deleteSelected() {
    if (!vm.selected) return;
    setConfirmDelete(false);
    setWorking(true);
    try {
      await getApi().remove(vm.selected.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorking(false);
    }
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
        <Button type="button" variant="outline" onClick={downloadSelected} disabled={!vm.selected}>
          Скачати
        </Button>
        <Button type="button" variant="destructive" onClick={() => setConfirmDelete(true)} disabled={!vm.selected}>
          Видалити
        </Button>
      </div>
      {error && <p className="text-destructive">{error}</p>}
      <SyncPanel onSynced={refresh} />
      <div className="drive-body">
        <UploadDropzone onFiles={uploadFiles} busy={working}>
          <FileTable
            files={vm.visibleFiles}
            columns={vm.columns}
            selected={vm.selected}
            onSelect={(f) => update((m) => m.select(f))}
            onDragStart={(f, e) => {
              e.preventDefault();
              window.minidrive.file.dragOut(f);
            }}
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

import { useCallback, useEffect, useState } from 'react';
import type { FileDto, UserDto } from '@minidrive/shared';
import { ColumnToggle, FileTable, FilterControl, PreviewPanel, SortControl, UploadDropzone, useDrive } from '@minidrive/ui';
import { getApi } from '../api';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const { vm, refresh, update, busy, error, setError } = useDrive(getApi(), onLogout);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

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
    if (!vm.selected || !confirm(`Видалити «${vm.selected.name}»?`)) return;
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
      <header>
        <strong>MiniDrive</strong>
        <span>{user.username}</span>
        <button type="button" onClick={onLogout}>Вийти</button>
      </header>
      <div className="toolbar">
        <SortControl order={vm.order} onChange={(o) => update((m) => m.setOrder(o))} />
        <FilterControl filter={vm.filter} onChange={(f) => update((m) => m.setFilter(f))} />
        <ColumnToggle columns={vm.columns} onToggle={(k) => update((m) => m.toggleColumn(k))} />
        <button type="button" onClick={refresh} disabled={busy}>Оновити</button>
        <button type="button" onClick={downloadSelected} disabled={!vm.selected}>Вивантажити</button>
        <button type="button" onClick={deleteSelected} disabled={!vm.selected}>Видалити</button>
      </div>
      {error && <p className="error">{error}</p>}
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
    </div>
  );
}

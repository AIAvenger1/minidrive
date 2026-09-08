import { useCallback } from 'react';
import type { FileDto, UserDto } from '@minidrive/shared';
import { DriveWorkspace, getApi } from '@minidrive/ui';
import { SyncPanel } from '../components/SyncPanel';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const saveFile = useCallback(async (file: FileDto, blob: Blob) => {
    await window.minidrive.file.saveAs(file.name, await blob.arrayBuffer());
  }, []);
  const subscribeErrors = useCallback(
    (report: (message: string) => void) => window.minidrive.file.onDragOutError(report),
    [],
  );

  return (
    <DriveWorkspace
      user={user}
      api={getApi()}
      onLogout={onLogout}
      saveFile={saveFile}
      onRowDragStart={(f, e) => {
        e.preventDefault();
        window.minidrive.file.dragOut(f);
      }}
      subscribeErrors={subscribeErrors}
      renderSyncPanel={(onSynced) => <SyncPanel onSynced={onSynced} />}
    />
  );
}

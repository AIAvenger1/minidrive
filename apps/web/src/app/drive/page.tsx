'use client';

import { DriveWorkspace, getApi } from '@minidrive/ui';
import { useSession } from '../../hooks/useSession';
import { saveBlob } from '../../lib/download';
import { SyncPanel } from '../../components/SyncPanel';

export default function DrivePage() {
  const { user, ready, logout } = useSession();

  if (!ready || !user) return null;
  return (
    <DriveWorkspace
      user={user}
      api={getApi()}
      onLogout={logout}
      saveFile={(file, blob) => saveBlob(file.name, blob)}
      renderSyncPanel={(onSynced) => <SyncPanel onSynced={onSynced} />}
    />
  );
}

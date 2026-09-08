import { useEffect } from 'react';
import type { UserDto } from '@minidrive/shared';
import { ColumnToggle, FileTable, FilterControl, SortControl, useDrive } from '@minidrive/ui';
import { getApi } from '../api';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const { vm, refresh, update, busy, error } = useDrive(getApi(), onLogout);

  useEffect(() => {
    refresh();
  }, [refresh]);

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
      </div>
      {error && <p className="error">{error}</p>}
      <FileTable files={vm.visibleFiles} columns={vm.columns} selected={vm.selected} onSelect={(f) => update((m) => m.select(f))} />
    </div>
  );
}

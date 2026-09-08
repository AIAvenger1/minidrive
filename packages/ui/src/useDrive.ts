import { useCallback, useMemo, useReducer, useState } from 'react';
import { ApiClient, ApiError, DriveViewModel } from '@minidrive/shared';

export function useDrive(api: ApiClient, onUnauthorized: () => void) {
  const vm = useMemo(() => new DriveViewModel(), []);
  const [, rerender] = useReducer((n: number) => n + 1, 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      vm.setFiles(await api.listFiles());
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) onUnauthorized();
      else setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      rerender();
    }
  }, [vm, api, onUnauthorized]);

  const update = useCallback((fn: (vm: DriveViewModel) => void) => {
    fn(vm);
    rerender();
  }, [vm]);

  return { vm, refresh, update, busy, error, setError };
}

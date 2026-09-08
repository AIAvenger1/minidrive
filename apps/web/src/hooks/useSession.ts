import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { UserDto } from '@minidrive/shared';
import { getApi } from '@minidrive/ui';
import { SessionStore } from '../lib/session';

export function useSession() {
  const router = useRouter();
  const [user, setUser] = useState<UserDto | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!SessionStore.load()) {
      router.replace('/login');
      return;
    }
    getApi()
      .me()
      .then(setUser)
      .catch(() => {
        SessionStore.clear();
        router.replace('/login');
      })
      .finally(() => setReady(true));
  }, [router]);

  const logout = useCallback(() => {
    SessionStore.clear();
    router.replace('/login');
  }, [router]);

  return { user, ready, logout };
}

import { useCallback, useEffect, useState } from 'react';
import { ApiError, type UserDto } from '@minidrive/shared';
import { getApi } from '@minidrive/ui';
import { LoginScreen } from './screens/LoginScreen';
import { DriveScreen } from './screens/DriveScreen';
import { SessionStore } from './session';

export default function App() {
  const [user, setUser] = useState<UserDto | null>(null);
  const [apiUrl, setApiUrl] = useState('http://localhost:3000');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    SessionStore.load()
      .then(async (s) => {
        setApiUrl(s.apiUrl);
        if (s.token) setUser(await getApi().me());
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) SessionStore.clear();
      })
      .finally(() => setReady(true));
  }, []);

  const onLogout = useCallback(async () => {
    await SessionStore.clear();
    setUser(null);
  }, []);

  if (!ready) return null;
  if (!user) return <LoginScreen apiUrl={apiUrl} onLoggedIn={setUser} />;
  return <DriveScreen user={user} onLogout={onLogout} />;
}

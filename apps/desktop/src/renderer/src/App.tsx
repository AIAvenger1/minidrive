import { useEffect, useState } from 'react';
import { ApiError, type UserDto } from '@minidrive/shared';
import { getApi } from './api';
import { LoginScreen } from './screens/LoginScreen';
import { DriveScreen } from './screens/DriveScreen';
import { SessionStore } from './session';

export default function App() {
  const [user, setUser] = useState<UserDto | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    SessionStore.load()
      .then(async (s) => {
        if (s.token) setUser(await getApi().me());
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) SessionStore.clear();
      })
      .finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return <LoginScreen onLoggedIn={setUser} />;
  return (
    <DriveScreen
      user={user}
      onLogout={async () => {
        await SessionStore.clear();
        setUser(null);
      }}
    />
  );
}

import { useEffect, useState } from 'react';
import { ApiError, type UserDto } from '@minidrive/shared';
import { configureApi } from '../api';
import { SessionStore } from '../session';

type Props = { onLoggedIn: (user: UserDto) => void };

export function LoginScreen({ onLoggedIn }: Props) {
  const [apiUrl, setApiUrl] = useState('http://localhost:3000');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    SessionStore.load().then((s) => setApiUrl(s.apiUrl));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const api = configureApi(apiUrl.trim().replace(/\/+$/, ''), null);
      const res = mode === 'login' ? await api.login(username, password) : await api.register(username, password);
      await SessionStore.save(res.accessToken, api.baseUrl);
      onLoggedIn(res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Сервер недоступний');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <h1>MiniDrive</h1>
        <label>
          Адреса сервера
          <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://localhost:3000" />
        </label>
        <label>
          Ім'я користувача
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {mode === 'login' ? 'Увійти' : 'Зареєструватися'}
        </button>
        <button type="button" className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Уже є обліковий запис? Увійти'}
        </button>
      </form>
    </div>
  );
}

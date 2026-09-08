import { useState } from 'react';
import { ApiError, type UserDto } from '@minidrive/shared';
import { Alert, AlertDescription, Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@minidrive/ui';
import { CircleAlert } from 'lucide-react';
import { configureApi } from '../api';
import { SessionStore } from '../session';

type Props = { apiUrl: string; onLoggedIn: (user: UserDto) => void };

export function LoginScreen({ apiUrl: initialApiUrl, onLoggedIn }: Props) {
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const api = configureApi(apiUrl, null);
      const res = mode === 'login' ? await api.login(username, password) : await api.register(username, password);
      await SessionStore.save(res.accessToken, api.baseUrl);
      onLoggedIn(res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Сервер недоступний');
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setMode(mode === 'login' ? 'register' : 'login');
    setError(null);
  }

  return (
    <div className="login">
      <Card className="w-[360px]">
        <CardHeader>
          <CardTitle className="text-xl">MiniDrive</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={submit}>
            <div className="grid gap-1.5">
              <Label htmlFor="apiUrl">Адреса сервера</Label>
              <Input
                id="apiUrl"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:3000"
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="username">Ім'я користувача</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="password">Пароль</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && (
              <Alert variant="destructive" aria-live="polite">
                <CircleAlert />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" disabled={busy}>
              {mode === 'login' ? 'Увійти' : 'Зареєструватися'}
            </Button>
            <Button type="button" variant="link" onClick={switchMode}>
              {mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Уже є обліковий запис? Увійти'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

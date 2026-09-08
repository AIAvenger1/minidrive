import { useState, type FormEvent } from 'react';
import { ApiError, type AuthResponseDto } from '@minidrive/shared';
import { CircleAlert } from 'lucide-react';
import { configureApi } from './apiRegistry';
import { Alert, AlertDescription } from './components/ui/alert';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';

type Props = {
  apiUrl: string;
  allowServerChange?: boolean;
  onAuthenticated: (result: AuthResponseDto, apiUrl: string) => Promise<void> | void;
};

export function LoginForm({ apiUrl: initialApiUrl, allowServerChange = false, onAuthenticated }: Props) {
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const api = configureApi(apiUrl, null);
      const result = mode === 'login' ? await api.login(username, password) : await api.register(username, password);
      await onAuthenticated(result, api.baseUrl);
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
    <Card className="w-[360px]">
      <CardHeader>
        <CardTitle className="text-xl">MiniDrive</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={submit}>
          {allowServerChange ? (
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
          ) : (
            <p className="text-sm text-muted-foreground">Сервер: {apiUrl}</p>
          )}
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
          <Button type="button" variant="link" className="h-auto whitespace-normal" onClick={switchMode}>
            {mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Уже є обліковий запис? Увійти'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

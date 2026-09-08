import type { UserDto } from '@minidrive/shared';
import { LoginForm } from '@minidrive/ui';
import { SessionStore } from '../session';

type Props = { apiUrl: string; onLoggedIn: (user: UserDto) => void };

export function LoginScreen({ apiUrl, onLoggedIn }: Props) {
  return (
    <div className="login">
      <LoginForm
        apiUrl={apiUrl}
        allowServerChange
        onAuthenticated={async (result, url) => {
          await SessionStore.save(result.accessToken, url);
          onLoggedIn(result.user);
        }}
      />
    </div>
  );
}

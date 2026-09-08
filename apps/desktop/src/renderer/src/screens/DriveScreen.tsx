import type { UserDto } from '@minidrive/shared';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  return (
    <div className="drive">
      <header>
        <h1>MiniDrive</h1>
        <span>{user.username}</span>
        <button type="button" onClick={onLogout}>
          Вийти
        </button>
      </header>
    </div>
  );
}

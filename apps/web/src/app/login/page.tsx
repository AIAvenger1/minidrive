'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoginForm } from '@minidrive/ui';
import { API_URL, SessionStore } from '../../lib/session';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    if (SessionStore.load()) router.replace('/drive');
  }, [router]);

  return (
    <main className="login">
      <LoginForm
        apiUrl={API_URL}
        onAuthenticated={(result) => {
          SessionStore.save(result.accessToken);
          router.replace('/drive');
        }}
      />
    </main>
  );
}

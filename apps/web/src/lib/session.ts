import { configureApi } from '@minidrive/ui';

const TOKEN_KEY = 'minidrive.token';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3000';

export const SessionStore = {
  load(): string | null {
    const token = window.localStorage.getItem(TOKEN_KEY);
    configureApi(API_URL, token);
    return token;
  },
  save(token: string) {
    window.localStorage.setItem(TOKEN_KEY, token);
    configureApi(API_URL, token);
  },
  clear() {
    window.localStorage.removeItem(TOKEN_KEY);
    configureApi(API_URL, null);
  },
};

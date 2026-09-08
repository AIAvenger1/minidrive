import Store from 'electron-store';
import { app, safeStorage } from 'electron';

export type Settings = { apiUrl: string; token: string | null; boundFolder: string | null; autoWatch: boolean };

export const DEFAULT_API_URL = app.isPackaged ? 'https://minidrive.trelawney.tech/api' : 'http://localhost:3000';

const store = new Store<{ apiUrl: string; tokenEncrypted: string | null; boundFolder: string | null; autoWatch: boolean }>({
  defaults: { apiUrl: DEFAULT_API_URL, tokenEncrypted: null, boundFolder: null, autoWatch: false },
});

export function getSettings(): Settings {
  return {
    apiUrl: store.get('apiUrl'),
    token: decrypt(store.get('tokenEncrypted')),
    boundFolder: store.get('boundFolder'),
    autoWatch: store.get('autoWatch'),
  };
}

export function updateSettings(patch: Partial<Omit<Settings, 'token'>>): Settings {
  if (patch.apiUrl !== undefined) store.set('apiUrl', patch.apiUrl);
  if (patch.boundFolder !== undefined) store.set('boundFolder', patch.boundFolder);
  if (patch.autoWatch !== undefined) store.set('autoWatch', patch.autoWatch);
  return getSettings();
}

export function setToken(token: string | null): void {
  if (!token) {
    store.set('tokenEncrypted', null);
    return;
  }
  const value = safeStorage.isEncryptionAvailable()
    ? safeStorage.encryptString(token).toString('base64')
    : Buffer.from(token, 'utf8').toString('base64');
  store.set('tokenEncrypted', value);
}

function decrypt(value: string | null): string | null {
  if (!value) return null;
  const buffer = Buffer.from(value, 'base64');
  try {
    return safeStorage.isEncryptionAvailable() ? safeStorage.decryptString(buffer) : buffer.toString('utf8');
  } catch {
    store.set('tokenEncrypted', null);
    return null;
  }
}

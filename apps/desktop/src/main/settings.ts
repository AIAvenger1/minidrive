import Store from 'electron-store';
import { safeStorage } from 'electron';

export type Settings = { apiUrl: string; token: string | null; boundFolder: string | null; autoWatch: boolean };

const store = new Store<{ apiUrl: string; tokenEncrypted: string | null; boundFolder: string | null; autoWatch: boolean }>({
  defaults: { apiUrl: 'http://localhost:3000', tokenEncrypted: null, boundFolder: null, autoWatch: false },
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
  if (patch.apiUrl !== undefined) store.set('apiUrl', patch.apiUrl.replace(/\/+$/, ''));
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
  return safeStorage.isEncryptionAvailable() ? safeStorage.decryptString(buffer) : buffer.toString('utf8');
}

import { configureApi } from '@minidrive/ui';

export const SessionStore = {
  async load() {
    const settings = await window.minidrive.settings.get();
    configureApi(settings.apiUrl, settings.token);
    return { token: settings.token, apiUrl: settings.apiUrl };
  },
  async save(token: string, apiUrl: string) {
    await window.minidrive.settings.set({ apiUrl });
    await window.minidrive.session.setToken(token);
    configureApi(apiUrl, token);
  },
  async clear() {
    await window.minidrive.session.setToken(null);
    const settings = await window.minidrive.settings.get();
    configureApi(settings.apiUrl, null);
  },
};

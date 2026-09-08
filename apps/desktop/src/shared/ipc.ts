import type { Settings } from '../main/settings';

export const CHANNELS = {
  settingsGet: 'settings:get',
  settingsSet: 'settings:set',
  sessionSetToken: 'session:setToken',
  sessionGetToken: 'session:getToken',
  folderPick: 'folder:pick',
  syncRun: 'sync:run',
  syncWatch: 'sync:watch',
  syncStatus: 'sync:status',
  syncProgress: 'sync:progress',
  syncAuto: 'sync:auto',
  fileSaveAs: 'file:saveAs',
  fileDragOut: 'file:dragOut',
  fileDragOutError: 'file:dragOutError',
} as const;

export type StoredSettings = Settings;

export type SettingsPatch = { apiUrl?: string };

export type SyncStatus = {
  syncing: boolean;
  watching: boolean;
  boundFolder: string | null;
  autoWatch: boolean;
};

export type SyncProgress = { done: number; total: number };

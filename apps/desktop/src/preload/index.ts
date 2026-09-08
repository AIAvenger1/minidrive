import { contextBridge, ipcRenderer } from 'electron';
import type { FileDto, SyncReport } from '@minidrive/shared';
import { CHANNELS, type SettingsPatch, type StoredSettings, type SyncProgress, type SyncStatus } from '../shared/ipc';

const minidrive = {
  settings: {
    get: (): Promise<StoredSettings> => ipcRenderer.invoke(CHANNELS.settingsGet),
    set: (patch: SettingsPatch): Promise<StoredSettings> => ipcRenderer.invoke(CHANNELS.settingsSet, patch),
  },
  session: {
    setToken: (token: string | null): Promise<void> => ipcRenderer.invoke(CHANNELS.sessionSetToken, token),
    getToken: (): Promise<string | null> => ipcRenderer.invoke(CHANNELS.sessionGetToken),
  },
  folder: {
    pick: (): Promise<string | null> => ipcRenderer.invoke(CHANNELS.folderPick),
  },
  sync: {
    run: (): Promise<SyncReport> => ipcRenderer.invoke(CHANNELS.syncRun),
    watch: (enabled: boolean): Promise<boolean> => ipcRenderer.invoke(CHANNELS.syncWatch, enabled),
    status: (): Promise<SyncStatus> => ipcRenderer.invoke(CHANNELS.syncStatus),
    onProgress: (cb: (p: SyncProgress) => void) => {
      const listener = (_: unknown, p: SyncProgress) => cb(p);
      ipcRenderer.on(CHANNELS.syncProgress, listener);
      return () => ipcRenderer.removeListener(CHANNELS.syncProgress, listener);
    },
    onAutoSync: (cb: (report: SyncReport) => void) => {
      const listener = (_: unknown, r: SyncReport) => cb(r);
      ipcRenderer.on(CHANNELS.syncAuto, listener);
      return () => ipcRenderer.removeListener(CHANNELS.syncAuto, listener);
    },
  },
  file: {
    saveAs: (name: string, bytes: ArrayBuffer): Promise<string | null> => ipcRenderer.invoke(CHANNELS.fileSaveAs, name, bytes),
    dragOut: (file: FileDto): void => ipcRenderer.send(CHANNELS.fileDragOut, file),
    onDragOutError: (cb: (message: string) => void) => {
      const listener = (_: unknown, message: string) => cb(message);
      ipcRenderer.on(CHANNELS.fileDragOutError, listener);
      return () => ipcRenderer.removeListener(CHANNELS.fileDragOutError, listener);
    },
  },
};

contextBridge.exposeInMainWorld('minidrive', minidrive);

export type MinidriveApi = typeof minidrive;

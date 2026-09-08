import { contextBridge, ipcRenderer } from 'electron';

const minidrive = {
  settings: {
    get: () => ipcRenderer.invoke('settings:get'),
    set: (patch: Record<string, unknown>) => ipcRenderer.invoke('settings:set', patch),
  },
  session: {
    setToken: (token: string | null) => ipcRenderer.invoke('session:setToken', token),
    getToken: () => ipcRenderer.invoke('session:getToken'),
  },
  folder: { pick: () => ipcRenderer.invoke('folder:pick') },
  sync: {
    run: () => ipcRenderer.invoke('sync:run'),
    watch: (enabled: boolean) => ipcRenderer.invoke('sync:watch', enabled),
    status: () => ipcRenderer.invoke('sync:status'),
    onProgress: (cb: (p: { done: number; total: number }) => void) => {
      const listener = (_: unknown, p: { done: number; total: number }) => cb(p);
      ipcRenderer.on('sync:progress', listener);
      return () => ipcRenderer.removeListener('sync:progress', listener);
    },
    onAutoSync: (cb: (report: unknown) => void) => {
      const listener = (_: unknown, r: unknown) => cb(r);
      ipcRenderer.on('sync:auto', listener);
      return () => ipcRenderer.removeListener('sync:auto', listener);
    },
  },
  file: {
    saveAs: (name: string, bytes: ArrayBuffer) => ipcRenderer.invoke('file:saveAs', name, bytes),
    dragOut: (file: unknown) => ipcRenderer.send('file:dragOut', file),
    onDragOutError: (cb: (message: string) => void) => {
      const listener = (_: unknown, message: string) => cb(message);
      ipcRenderer.on('file:dragOutError', listener);
      return () => ipcRenderer.removeListener('file:dragOutError', listener);
    },
  },
};

contextBridge.exposeInMainWorld('minidrive', minidrive);

export type MinidriveApi = typeof minidrive;

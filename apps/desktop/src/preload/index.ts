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
  file: {
    saveAs: (name: string, bytes: ArrayBuffer) => ipcRenderer.invoke('file:saveAs', name, bytes),
  },
};

contextBridge.exposeInMainWorld('minidrive', minidrive);

export type MinidriveApi = typeof minidrive;

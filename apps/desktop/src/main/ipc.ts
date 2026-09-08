import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { promises as fs } from 'fs';
import { join } from 'path';
import { ApiClient, type FileDto } from '@minidrive/shared';
import { DragOutHandler } from './dragOutHandler';
import { getSettings, setToken, updateSettings } from './settings';
import { FolderWatcher } from './sync/folderWatcher';
import { SyncEngine } from './sync/syncEngine';

const watcher = new FolderWatcher();
const dragOut = new DragOutHandler(join(__dirname, '../../resources/drag.png'));
let syncing = false;

function api(): ApiClient {
  const s = getSettings();
  return new ApiClient(s.apiUrl, s.token);
}

async function runSync(win: BrowserWindow) {
  const { boundFolder } = getSettings();
  if (!boundFolder) throw new Error("Папку не прив'язано");
  if (syncing) throw new Error('Синхронізація вже виконується');
  syncing = true;
  try {
    return await new SyncEngine(api()).synchronize(boundFolder, (done, total) => win.webContents.send('sync:progress', { done, total }));
  } finally {
    syncing = false;
  }
}

function setWatch(win: BrowserWindow, enabled: boolean): boolean {
  const { boundFolder } = getSettings();
  updateSettings({ autoWatch: enabled });
  if (!enabled || !boundFolder) {
    watcher.stop();
    return false;
  }
  watcher.start(boundFolder, async () => {
    if (syncing) return;
    try {
      win.webContents.send('sync:auto', await runSync(win));
    } catch (err) {
      win.webContents.send('sync:auto', { uploaded: 0, downloaded: 0, skipped: 0, failed: 1, errors: [(err as Error).message] });
    }
  });
  return true;
}

export function registerIpc(win: BrowserWindow): void {
  ipcMain.handle('settings:get', () => getSettings());
  ipcMain.handle('settings:set', (_e, patch) => updateSettings(patch));
  ipcMain.handle('session:setToken', (_e, token: string | null) => setToken(token));
  ipcMain.handle('session:getToken', () => getSettings().token);

  ipcMain.handle('file:saveAs', async (_e, name: string, bytes: ArrayBuffer) => {
    const { canceled, filePath } = await dialog.showSaveDialog(win, { defaultPath: name });
    if (canceled || !filePath) return null;
    await fs.writeFile(filePath, Buffer.from(bytes));
    return filePath;
  });
  ipcMain.on('file:dragOut', (e, file: FileDto) => {
    dragOut.startDrag(e.sender, api(), file).catch(() => undefined);
  });

  ipcMain.handle('folder:pick', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
    if (canceled || filePaths.length === 0) return null;
    updateSettings({ boundFolder: filePaths[0] });
    if (getSettings().autoWatch) setWatch(win, true);
    return filePaths[0];
  });
  ipcMain.handle('sync:run', () => runSync(win));
  ipcMain.handle('sync:watch', (_e, enabled: boolean) => setWatch(win, enabled));
  ipcMain.handle('sync:status', () => ({ syncing, watching: watcher.active, boundFolder: getSettings().boundFolder, autoWatch: getSettings().autoWatch }));

  if (getSettings().autoWatch) setWatch(win, true);
  app.on('before-quit', () => watcher.stop());
}

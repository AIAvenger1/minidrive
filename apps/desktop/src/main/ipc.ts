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

function broadcast(channel: string, payload: unknown): void {
  BrowserWindow.getAllWindows().forEach((w) => w.webContents.send(channel, payload));
}

async function runSync() {
  const { boundFolder } = getSettings();
  if (!boundFolder) throw new Error("Папку не прив'язано");
  if (syncing) throw new Error('Синхронізація вже виконується');
  syncing = true;
  watcher.pause();
  try {
    return await new SyncEngine(api()).synchronize(boundFolder, (done, total) => broadcast('sync:progress', { done, total }));
  } finally {
    syncing = false;
    watcher.resume();
  }
}

function setWatch(enabled: boolean): boolean {
  const { boundFolder } = getSettings();
  updateSettings({ autoWatch: enabled });
  if (!enabled || !boundFolder) {
    watcher.stop();
    return false;
  }
  watcher.start(boundFolder, async () => {
    if (syncing) return;
    try {
      broadcast('sync:auto', await runSync());
    } catch (err) {
      broadcast('sync:auto', { uploaded: 0, downloaded: 0, skipped: 0, failed: 1, errors: [(err as Error).message] });
    }
  });
  return true;
}

export function registerIpc(): void {
  ipcMain.handle('settings:get', () => getSettings());
  ipcMain.handle('settings:set', (_e, patch) => updateSettings(patch));
  ipcMain.handle('session:setToken', (_e, token: string | null) => setToken(token));
  ipcMain.handle('session:getToken', () => getSettings().token);

  ipcMain.handle('file:saveAs', async (e, name: string, bytes: ArrayBuffer) => {
    const win = BrowserWindow.fromWebContents(e.sender) ?? BrowserWindow.getAllWindows()[0];
    const { canceled, filePath } = await dialog.showSaveDialog(win, { defaultPath: name });
    if (canceled || !filePath) return null;
    await fs.writeFile(filePath, Buffer.from(bytes));
    return filePath;
  });
  ipcMain.on('file:dragOut', (e, file: FileDto) => {
    dragOut.startDrag(e.sender, api(), file).catch((err) => {
      e.sender.send('file:dragOutError', (err as Error).message);
    });
  });

  ipcMain.handle('folder:pick', async (e) => {
    const win = BrowserWindow.fromWebContents(e.sender) ?? BrowserWindow.getAllWindows()[0];
    const { canceled, filePaths } = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
    if (canceled || filePaths.length === 0) return null;
    updateSettings({ boundFolder: filePaths[0] });
    if (getSettings().autoWatch) setWatch(true);
    return filePaths[0];
  });
  ipcMain.handle('sync:run', () => runSync());
  ipcMain.handle('sync:watch', (_e, enabled: boolean) => setWatch(enabled));
  ipcMain.handle('sync:status', () => ({ syncing, watching: watcher.active, boundFolder: getSettings().boundFolder, autoWatch: getSettings().autoWatch }));

  if (getSettings().autoWatch) setWatch(true);
  app.on('before-quit', () => watcher.stop());
}

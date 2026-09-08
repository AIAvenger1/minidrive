import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { promises as fs } from 'fs';
import { join } from 'path';
import { ApiClient, failedSyncReport, type FileDto } from '@minidrive/shared';
import { CHANNELS, type SettingsPatch, type SyncStatus } from '../shared/ipc';
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
    return await new SyncEngine(api()).synchronize(boundFolder, (done, total) => broadcast(CHANNELS.syncProgress, { done, total }));
  } finally {
    syncing = false;
    watcher.resume();
  }
}

function setWatch(enabled: boolean): boolean {
  const { boundFolder } = getSettings();
  if (!enabled || !boundFolder) {
    updateSettings({ autoWatch: false });
    watcher.stop();
    return false;
  }
  updateSettings({ autoWatch: true });
  watcher.start(boundFolder, async () => {
    if (syncing) return;
    try {
      broadcast(CHANNELS.syncAuto, await runSync());
    } catch (err) {
      broadcast(CHANNELS.syncAuto, failedSyncReport((err as Error).message));
    }
  });
  return true;
}

export function restoreAutoWatch(): void {
  if (getSettings().autoWatch) setWatch(true);
}

export function registerIpc(): void {
  ipcMain.handle(CHANNELS.settingsGet, () => getSettings());
  ipcMain.handle(CHANNELS.settingsSet, (_e, patch: SettingsPatch) => updateSettings({ apiUrl: patch.apiUrl }));
  ipcMain.handle(CHANNELS.sessionSetToken, (_e, token: string | null) => setToken(token));
  ipcMain.handle(CHANNELS.sessionGetToken, () => getSettings().token);

  ipcMain.handle(CHANNELS.fileSaveAs, async (e, name: string, bytes: ArrayBuffer) => {
    const win = BrowserWindow.fromWebContents(e.sender);
    if (!win) return null;
    const { canceled, filePath } = await dialog.showSaveDialog(win, { defaultPath: name });
    if (canceled || !filePath) return null;
    await fs.writeFile(filePath, Buffer.from(bytes));
    return filePath;
  });
  ipcMain.on(CHANNELS.fileDragOut, (e, file: FileDto) => {
    dragOut.startDrag(e.sender, api(), file).catch((err) => {
      if (!e.sender.isDestroyed()) e.sender.send(CHANNELS.fileDragOutError, (err as Error).message);
    });
  });

  ipcMain.handle(CHANNELS.folderPick, async (e) => {
    const win = BrowserWindow.fromWebContents(e.sender);
    if (!win) return null;
    const { canceled, filePaths } = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
    if (canceled || filePaths.length === 0) return null;
    updateSettings({ boundFolder: filePaths[0] });
    if (getSettings().autoWatch) setWatch(true);
    return filePaths[0];
  });
  ipcMain.handle(CHANNELS.syncRun, () => runSync());
  ipcMain.handle(CHANNELS.syncWatch, (_e, enabled: boolean) => setWatch(enabled));
  ipcMain.handle(
    CHANNELS.syncStatus,
    (): SyncStatus => ({ syncing, watching: watcher.active, boundFolder: getSettings().boundFolder, autoWatch: getSettings().autoWatch }),
  );

  app.on('before-quit', () => watcher.stop());
}

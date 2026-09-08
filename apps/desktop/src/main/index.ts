import { app, BrowserWindow, shell } from 'electron';
import { rmSync } from 'fs';
import { join } from 'path';
import { electronApp, is, optimizer } from '@electron-toolkit/utils';
import { registerIpc, restoreAutoWatch } from './ipc';

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), sandbox: false },
  });
  win.on('ready-to-show', () => win.show());
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  if (is.dev && process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'));
  }
  return win;
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('ua.knu.minidrive');
  app.on('browser-window-created', (_, window) => optimizer.watchWindowShortcuts(window));
  app.on('web-contents-created', (_, contents) => {
    contents.on('will-navigate', (e, url) => {
      if (url !== contents.getURL()) e.preventDefault();
    });
  });
  registerIpc();
  createWindow();
  restoreAutoWatch();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  rmSync(join(app.getPath('temp'), 'minidrive'), { recursive: true, force: true });
});

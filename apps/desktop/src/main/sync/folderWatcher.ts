import chokidar, { type FSWatcher } from 'chokidar';

const DEBOUNCE_MS = 2000;

export class FolderWatcher {
  private watcher: FSWatcher | null = null;
  private timer: NodeJS.Timeout | null = null;

  start(dir: string, onChange: () => void): void {
    this.stop();
    this.watcher = chokidar.watch(dir, { ignoreInitial: true, depth: 0, ignored: /(^|[\/\\])\../ });
    this.watcher.on('all', () => {
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(onChange, DEBOUNCE_MS);
    });
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.watcher?.close();
    this.watcher = null;
  }

  get active(): boolean {
    return this.watcher !== null;
  }
}

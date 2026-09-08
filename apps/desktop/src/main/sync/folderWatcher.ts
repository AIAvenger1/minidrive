import chokidar, { type FSWatcher } from 'chokidar';

const DEBOUNCE_MS = 2000;
const COOLDOWN_MS = 3000;

export class FolderWatcher {
  private watcher: FSWatcher | null = null;
  private timer: NodeJS.Timeout | null = null;
  private cooldownTimer: NodeJS.Timeout | null = null;
  private paused = false;

  start(dir: string, onChange: () => void): void {
    this.stop();
    this.watcher = chokidar.watch(dir, { ignoreInitial: true, depth: 0, ignored: /(^|[\/\\])\../ });
    this.watcher.on('all', () => {
      if (this.paused) return;
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(onChange, DEBOUNCE_MS);
    });
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.cooldownTimer) clearTimeout(this.cooldownTimer);
    this.cooldownTimer = null;
    this.paused = false;
    this.watcher?.close();
    this.watcher = null;
  }

  pause(): void {
    this.paused = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.cooldownTimer) clearTimeout(this.cooldownTimer);
    this.cooldownTimer = null;
  }

  resume(): void {
    if (this.cooldownTimer) clearTimeout(this.cooldownTimer);
    this.cooldownTimer = setTimeout(() => {
      this.paused = false;
      this.cooldownTimer = null;
    }, COOLDOWN_MS);
  }

  get active(): boolean {
    return this.watcher !== null;
  }
}

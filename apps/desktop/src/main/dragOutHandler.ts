import { app, type WebContents } from 'electron';
import { mkdir, writeFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import type { ApiClient, FileDto } from '@minidrive/shared';

export class DragOutHandler {
  constructor(private readonly iconPath: string) {}

  async startDrag(sender: WebContents, api: ApiClient, file: FileDto): Promise<void> {
    const dir = join(app.getPath('temp'), 'minidrive', file.id, String(Date.parse(file.updatedAt)));
    const target = join(dir, file.name);
    if (!existsSync(target)) {
      await mkdir(dir, { recursive: true });
      const blob = await api.download(file.id);
      await writeFile(target, Buffer.from(await blob.arrayBuffer()));
    }
    sender.startDrag({ file: target, icon: this.iconPath });
  }
}

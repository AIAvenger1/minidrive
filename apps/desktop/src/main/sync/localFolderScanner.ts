import { readdir, stat } from 'fs/promises';
import { join } from 'path';
import { isSyncableName, type LocalFileInfo } from '@minidrive/shared';

export const LocalFolderScanner = {
  async scan(dir: string): Promise<LocalFileInfo[]> {
    const entries = await readdir(dir, { withFileTypes: true });
    const files: LocalFileInfo[] = [];
    for (const entry of entries) {
      if (!entry.isFile() || !isSyncableName(entry.name)) continue;
      const s = await stat(join(dir, entry.name));
      files.push({ name: entry.name, size: s.size, mtime: s.mtimeMs });
    }
    return files;
  },
};

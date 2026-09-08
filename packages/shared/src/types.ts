export type FileDto = {
  id: string;
  name: string;
  extension: string;
  size: number;
  createdAt: string;
  updatedAt: string;
  uploadedBy: string;
  modifiedBy: string;
};

export type UserDto = { id: string; username: string };
export type AuthResponseDto = { accessToken: string; user: UserDto };

export type SortOrder = 'asc' | 'desc';
export type FileFilter = 'all' | 'cpp' | 'png';

export type ColumnKey = 'name' | 'size' | 'extension' | 'createdAt' | 'updatedAt' | 'uploadedBy' | 'modifiedBy';
export type ColumnVisibility = Record<ColumnKey, boolean>;

export type PreviewKind = 'text' | 'image' | 'none';

export type LocalFileInfo = { name: string; size: number; mtime: number };

export type SyncActionKind = 'upload' | 'download' | 'skip';
export type SyncAction = { kind: SyncActionKind; name: string; reason: string };
export type SyncPlan = { uploads: SyncAction[]; downloads: SyncAction[]; skipped: SyncAction[] };
export type SyncReport = { uploaded: number; downloaded: number; skipped: number; failed: number; errors: string[] };

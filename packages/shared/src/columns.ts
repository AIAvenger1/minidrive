import type { ColumnKey, ColumnVisibility } from './types';

export const COLUMN_KEYS: ColumnKey[] = ['name', 'extension', 'size', 'createdAt', 'updatedAt', 'uploadedBy', 'modifiedBy'];

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  name: 'Назва',
  extension: 'Тип',
  size: 'Розмір',
  createdAt: 'Створено',
  updatedAt: 'Змінено',
  uploadedBy: 'Завантажив',
  modifiedBy: 'Редагував',
};

export const DEFAULT_COLUMNS: ColumnVisibility = {
  name: true, extension: true, size: true, createdAt: true, updatedAt: true, uploadedBy: true, modifiedBy: true,
};

export function toggleColumn(visibility: ColumnVisibility, key: ColumnKey): ColumnVisibility {
  if (key === 'name') return { ...visibility, name: true };
  return { ...visibility, [key]: !visibility[key] };
}

export function hideAllButName(): ColumnVisibility {
  return { ...DEFAULT_COLUMNS, extension: false, size: false, createdAt: false, updatedAt: false, uploadedBy: false, modifiedBy: false };
}

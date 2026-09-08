import type { FileDto, FileFilter, SortOrder } from './types';

const VARIANT_FILTER_EXTENSIONS = new Set(['cpp', 'png']);

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  if (dot <= 0) return '';
  return name.slice(dot + 1).toLowerCase();
}

export function sortByName(files: FileDto[], order: SortOrder): FileDto[] {
  const direction = order === 'asc' ? 1 : -1;
  return [...files].sort(
    (a, b) => direction * a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }),
  );
}

export function filterByType(files: FileDto[], filter: FileFilter): FileDto[] {
  if (filter === 'all') return files;
  return files.filter((f) => VARIANT_FILTER_EXTENSIONS.has(extensionOf(f.name)));
}

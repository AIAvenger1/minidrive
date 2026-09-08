import { DEFAULT_COLUMNS, toggleColumn } from './columns';
import { filterByType, sortByName } from './fileList';
import type { ColumnKey, ColumnVisibility, FileDto, FileFilter, SortOrder } from './types';

export class DriveViewModel {
  files: FileDto[] = [];
  order: SortOrder = 'asc';
  filter: FileFilter = 'all';
  columns: ColumnVisibility = DEFAULT_COLUMNS;
  selected: FileDto | null = null;

  setFiles(files: FileDto[]): void {
    this.files = files;
    if (this.selected && !files.some((f) => f.id === this.selected!.id)) this.selected = null;
  }

  setOrder(order: SortOrder): void {
    this.order = order;
  }

  setFilter(filter: FileFilter): void {
    this.filter = filter;
  }

  toggleColumn(key: ColumnKey): void {
    this.columns = toggleColumn(this.columns, key);
  }

  select(file: FileDto | null): void {
    this.selected = file;
  }

  get visibleFiles(): FileDto[] {
    return filterByType(sortByName(this.files, this.order), this.filter);
  }
}

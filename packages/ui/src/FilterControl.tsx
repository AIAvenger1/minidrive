import type { FileFilter } from '@minidrive/shared';

export function FilterControl({ filter, onChange }: { filter: FileFilter; onChange: (f: FileFilter) => void }) {
  return (
    <select value={filter} onChange={(e) => onChange(e.target.value as FileFilter)} title="Фільтр за типом">
      <option value="all">Усі файли</option>
      <option value="cpp-png">Лише .cpp, .png</option>
    </select>
  );
}

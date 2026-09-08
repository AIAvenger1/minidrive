import type { FileFilter } from '@minidrive/shared';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';

export function FilterControl({ filter, onChange }: { filter: FileFilter; onChange: (f: FileFilter) => void }) {
  return (
    <Select value={filter} onValueChange={(v) => onChange(v as FileFilter)}>
      <SelectTrigger className="w-[180px]" title="Фільтр за типом">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Усі файли</SelectItem>
        <SelectItem value="cpp">Лише .cpp</SelectItem>
        <SelectItem value="png">Лише .png</SelectItem>
      </SelectContent>
    </Select>
  );
}

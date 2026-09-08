import { COLUMN_KEYS, COLUMN_LABELS, type ColumnKey, type ColumnVisibility } from '@minidrive/shared';
import { Checkbox } from './components/ui/checkbox';
import { Label } from './components/ui/label';

export function ColumnToggle({ columns, onToggle }: { columns: ColumnVisibility; onToggle: (k: ColumnKey) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {COLUMN_KEYS.filter((k) => k !== 'name').map((k) => (
        <div key={k} className="flex items-center gap-2">
          <Checkbox id={`column-${k}`} checked={columns[k]} onCheckedChange={() => onToggle(k)} />
          <Label htmlFor={`column-${k}`}>{COLUMN_LABELS[k]}</Label>
        </div>
      ))}
    </div>
  );
}

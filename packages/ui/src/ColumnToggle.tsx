import { COLUMN_KEYS, COLUMN_LABELS, type ColumnKey, type ColumnVisibility } from '@minidrive/shared';

export function ColumnToggle({ columns, onToggle }: { columns: ColumnVisibility; onToggle: (k: ColumnKey) => void }) {
  return (
    <div className="columns">
      {COLUMN_KEYS.filter((k) => k !== 'name').map((k) => (
        <label key={k}>
          <input type="checkbox" checked={columns[k]} onChange={() => onToggle(k)} /> {COLUMN_LABELS[k]}
        </label>
      ))}
    </div>
  );
}

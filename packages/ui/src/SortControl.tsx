import type { SortOrder } from '@minidrive/shared';

export function SortControl({ order, onChange }: { order: SortOrder; onChange: (o: SortOrder) => void }) {
  return (
    <button type="button" onClick={() => onChange(order === 'asc' ? 'desc' : 'asc')} title="Сортування за назвою">
      Назва {order === 'asc' ? '↑' : '↓'}
    </button>
  );
}

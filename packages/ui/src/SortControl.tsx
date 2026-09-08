import { ArrowDownAZ, ArrowUpAZ } from 'lucide-react';
import type { SortOrder } from '@minidrive/shared';
import { Button } from './components/ui/button';

export function SortControl({ order, onChange }: { order: SortOrder; onChange: (o: SortOrder) => void }) {
  const Icon = order === 'asc' ? ArrowUpAZ : ArrowDownAZ;
  return (
    <Button variant="outline" size="sm" type="button" title="Сортування за назвою" onClick={() => onChange(order === 'asc' ? 'desc' : 'asc')}>
      <Icon />
      Назва
    </Button>
  );
}

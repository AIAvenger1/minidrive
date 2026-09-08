import { COLUMN_KEYS, COLUMN_LABELS, type ColumnVisibility, type FileDto } from '@minidrive/shared';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';

type Props = {
  files: FileDto[];
  columns: ColumnVisibility;
  selected: FileDto | null;
  onSelect: (file: FileDto) => void;
  onDragStart?: (file: FileDto, e: React.DragEvent) => void;
};

const fmtDate = (iso: string) => new Date(iso).toLocaleString('uk-UA');
const fmtSize = (n: number) => (n < 1024 ? `${n} Б` : n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} КБ` : `${(n / 1024 / 1024).toFixed(1)} МБ`);

export function FileTable({ files, columns, selected, onSelect, onDragStart }: Props) {
  const visible = COLUMN_KEYS.filter((k) => columns[k]);
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {visible.map((k) => (
            <TableHead key={k}>{COLUMN_LABELS[k]}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {files.map((f) => (
          <TableRow
            key={f.id}
            data-state={selected?.id === f.id ? 'selected' : undefined}
            className="cursor-pointer"
            onClick={() => onSelect(f)}
            draggable={Boolean(onDragStart)}
            onDragStart={(e) => onDragStart?.(f, e)}
          >
            {visible.map((k) => (
              <TableCell key={k}>
                {k === 'size' ? fmtSize(f.size) : k === 'createdAt' || k === 'updatedAt' ? fmtDate(f[k]) : f[k]}
              </TableCell>
            ))}
          </TableRow>
        ))}
        {files.length === 0 && (
          <TableRow>
            <TableCell colSpan={visible.length} className="py-8 text-center text-muted-foreground">
              Файлів немає
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

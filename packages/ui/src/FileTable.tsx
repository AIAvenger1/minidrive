import { COLUMN_KEYS, COLUMN_LABELS, type ColumnVisibility, type FileDto } from '@minidrive/shared';

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
    <table className="files">
      <thead>
        <tr>{visible.map((k) => <th key={k}>{COLUMN_LABELS[k]}</th>)}</tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr
            key={f.id}
            className={selected?.id === f.id ? 'selected' : ''}
            onClick={() => onSelect(f)}
            draggable={Boolean(onDragStart)}
            onDragStart={(e) => onDragStart?.(f, e)}
          >
            {visible.map((k) => (
              <td key={k}>
                {k === 'size' ? fmtSize(f.size) : k === 'createdAt' || k === 'updatedAt' ? fmtDate(f[k]) : f[k]}
              </td>
            ))}
          </tr>
        ))}
        {files.length === 0 && <tr><td colSpan={visible.length} className="empty">Файлів немає</td></tr>}
      </tbody>
    </table>
  );
}

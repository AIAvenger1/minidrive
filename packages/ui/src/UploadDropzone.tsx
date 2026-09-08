import { useRef, useState, type PropsWithChildren } from 'react';
import { Upload } from 'lucide-react';
import { Button } from './components/ui/button';
import { cn } from './lib/utils';

type Props = PropsWithChildren<{ onFiles: (files: File[]) => void; busy: boolean }>;

export function UploadDropzone({ onFiles, busy, children }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      className={cn(
        'relative min-h-[200px] overflow-auto rounded-lg border bg-background',
        over && 'border-2 border-dashed border-primary bg-primary/5'
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onFiles(Array.from(e.dataTransfer.files));
      }}
    >
      <input
        ref={input}
        type="file"
        multiple
        hidden
        onChange={(e) => {
          onFiles(Array.from(e.target.files ?? []));
          e.target.value = '';
        }}
      />
      <Button type="button" className="m-2" onClick={() => input.current?.click()} disabled={busy}>
        <Upload />
        Завантажити файли
      </Button>
      {children}
      {over && <div className="drop-hint">Відпустіть, щоб завантажити</div>}
    </div>
  );
}

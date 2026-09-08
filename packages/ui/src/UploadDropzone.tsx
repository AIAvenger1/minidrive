import { useRef, useState, type PropsWithChildren } from 'react';

type Props = PropsWithChildren<{ onFiles: (files: File[]) => void; busy: boolean }>;

export function UploadDropzone({ onFiles, busy, children }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      className={`dropzone${over ? ' over' : ''}`}
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
      <button type="button" onClick={() => input.current?.click()} disabled={busy}>Завантажити файли</button>
      {children}
      {over && <div className="drop-hint">Відпустіть, щоб завантажити</div>}
    </div>
  );
}

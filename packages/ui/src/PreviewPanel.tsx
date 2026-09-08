import { useEffect, useState } from 'react';
import { createPreview, type FileDto, type PreviewResult } from '@minidrive/shared';

type Props = { file: FileDto | null; loadContent: (file: FileDto) => Promise<Blob> };

export function PreviewPanel({ file, loadContent }: Props) {
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'unsupported' | 'error'>('idle');

  useEffect(() => {
    let cancelled = false;
    let url: string | null = null;
    setResult(null);
    if (!file) {
      setState('idle');
      return;
    }
    const preview = createPreview(file);
    if (!preview) {
      setState('unsupported');
      return;
    }
    setState('loading');
    loadContent(file)
      .then((blob) => preview.render(blob))
      .then((r) => {
        if (cancelled) {
          if (r.kind === 'image') URL.revokeObjectURL(r.url);
          return;
        }
        if (r.kind === 'image') url = r.url;
        setResult(r);
        setState('idle');
      })
      .catch(() => {
        if (!cancelled) setState('error');
      });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [file, loadContent]);

  if (!file) return <aside className="preview empty">Оберіть файл, щоб побачити вміст</aside>;
  return (
    <aside className="preview">
      <h3>{file.name}</h3>
      <dl>
        <dt>Створено</dt><dd>{new Date(file.createdAt).toLocaleString('uk-UA')}</dd>
        <dt>Змінено</dt><dd>{new Date(file.updatedAt).toLocaleString('uk-UA')}</dd>
        <dt>Завантажив</dt><dd>{file.uploadedBy}</dd>
        <dt>Редагував</dt><dd>{file.modifiedBy}</dd>
      </dl>
      {state === 'loading' && <p>Завантаження…</p>}
      {state === 'unsupported' && <p>Попередній перегляд для цього типу недоступний</p>}
      {state === 'error' && <p className="error">Не вдалося отримати вміст</p>}
      {result?.kind === 'text' && <pre>{result.text}</pre>}
      {result?.kind === 'image' && <img src={result.url} alt={file.name} />}
    </aside>
  );
}

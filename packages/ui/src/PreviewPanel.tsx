import { useEffect, useState } from 'react';
import { createPreview, type FileDto, type PreviewResult } from '@minidrive/shared';
import { CircleAlert } from 'lucide-react';
import { Alert, AlertDescription } from './components/ui/alert';
import { Badge } from './components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';

type Props = { file: FileDto | null; loadContent: (file: FileDto) => Promise<Blob> };

function extensionOf(name: string) {
  const i = name.lastIndexOf('.');
  return i === -1 ? '' : name.slice(i + 1).toLowerCase();
}

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

  if (!file) {
    return (
      <Card className="h-full">
        <CardContent className="flex h-full items-center justify-center text-muted-foreground">
          Оберіть файл, щоб побачити вміст
        </CardContent>
      </Card>
    );
  }

  const ext = extensionOf(file.name);

  return (
    <Card className="h-full overflow-auto">
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <CardTitle className="min-w-0 truncate">{file.name}</CardTitle>
        {ext && <Badge variant="secondary">.{ext}</Badge>}
      </CardHeader>
      <CardContent>
        <dl className="mb-4 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Створено</dt>
          <dd>{new Date(file.createdAt).toLocaleString('uk-UA')}</dd>
          <dt className="text-muted-foreground">Змінено</dt>
          <dd>{new Date(file.updatedAt).toLocaleString('uk-UA')}</dd>
          <dt className="text-muted-foreground">Завантажив</dt>
          <dd>{file.uploadedBy}</dd>
          <dt className="text-muted-foreground">Редагував</dt>
          <dd>{file.modifiedBy}</dd>
        </dl>
        {state === 'loading' && <p>Завантаження…</p>}
        {state === 'unsupported' && (
          <p className="text-muted-foreground">Попередній перегляд для цього типу недоступний</p>
        )}
        {state === 'error' && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>Не вдалося отримати вміст</AlertDescription>
          </Alert>
        )}
        {result?.kind === 'text' && (
          <pre className="whitespace-pre-wrap break-words font-mono text-xs">{result.text}</pre>
        )}
        {result?.kind === 'image' && <img className="h-auto max-w-full rounded" src={result.url} alt={file.name} />}
      </CardContent>
    </Card>
  );
}

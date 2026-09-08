import { extensionOf } from './fileList';
import type { FileDto, PreviewKind } from './types';

const TEXT_EXTENSIONS = new Set([
  'cs', 'cpp', 'c', 'h', 'hpp', 'txt', 'md', 'json', 'js', 'ts', 'py', 'java', 'kt', 'xml', 'html', 'css', 'yml', 'yaml', 'csv', 'log',
]);
const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']);

export function previewKindOf(name: string): PreviewKind {
  const ext = extensionOf(name);
  if (TEXT_EXTENSIONS.has(ext)) return 'text';
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  return 'none';
}

export type PreviewResult = { kind: 'text'; text: string } | { kind: 'image'; url: string };

export abstract class FilePreview {
  abstract readonly kind: PreviewKind;

  constructor(readonly entry: FileDto) {}

  canRender(ext: string): boolean {
    return previewKindOf(`f.${ext}`) === this.kind;
  }

  abstract render(content: Blob): Promise<PreviewResult>;
}

export class TextPreview extends FilePreview {
  readonly kind = 'text' as const;
  readonly encoding = 'utf-8';

  async render(content: Blob): Promise<PreviewResult> {
    return { kind: 'text', text: await content.text() };
  }
}

export class ImagePreview extends FilePreview {
  readonly kind = 'image' as const;

  async render(content: Blob): Promise<PreviewResult> {
    return { kind: 'image', url: URL.createObjectURL(content) };
  }
}

export function createPreview(entry: FileDto): FilePreview | null {
  switch (previewKindOf(entry.name)) {
    case 'text':
      return new TextPreview(entry);
    case 'image':
      return new ImagePreview(entry);
    default:
      return null;
  }
}

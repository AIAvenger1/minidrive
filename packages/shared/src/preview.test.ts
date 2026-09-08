import { afterEach, describe, expect, it, vi } from 'vitest';
import { createPreview, ImagePreview, previewKindOf, TextPreview } from './preview';
import type { FileDto } from './types';

const entry = (name: string): FileDto => ({
  id: 'x', name, extension: '', size: 1, createdAt: '', updatedAt: '', uploadedBy: 'a', modifiedBy: 'a',
});

describe('previewKindOf', () => {
  it('maps the variant types', () => {
    expect(previewKindOf('Program.cs')).toBe('text');
    expect(previewKindOf('photo.jpg')).toBe('image');
  });

  it('is generic for other text and image files', () => {
    expect(previewKindOf('main.cpp')).toBe('text');
    expect(previewKindOf('logo.PNG')).toBe('image');
    expect(previewKindOf('notes.md')).toBe('text');
  });

  it('returns none for unknown types', () => {
    expect(previewKindOf('archive.zip')).toBe('none');
    expect(previewKindOf('binary')).toBe('none');
  });
});

describe('createPreview', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('creates a TextPreview for .cs and renders the text', async () => {
    const p = createPreview(entry('Program.cs'));
    expect(p).toBeInstanceOf(TextPreview);
    const result = await p!.render(new Blob(['class A {}']));
    expect(result).toEqual({ kind: 'text', text: 'class A {}' });
  });

  it('creates an ImagePreview for .jpg and returns an object url', async () => {
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:img-1' });
    const p = createPreview(entry('photo.jpg'));
    expect(p).toBeInstanceOf(ImagePreview);
    expect(await p!.render(new Blob([]))).toEqual({ kind: 'image', url: 'blob:img-1' });
  });

  it('returns null when nothing can render the file', () => {
    expect(createPreview(entry('data.bin'))).toBeNull();
  });
});

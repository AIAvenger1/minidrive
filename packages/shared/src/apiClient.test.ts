import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError } from './apiClient';

const jsonResponse = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

describe('ApiClient', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('sends the bearer token and parses json', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [{ id: '1', name: 'a.txt' }]));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient('http://api.test', 'tok');
    const files = await api.listFiles();
    expect(files[0].name).toBe('a.txt');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api.test/files');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('throws ApiError with the status on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(401, { message: 'Unauthorized' })));
    const api = new ApiClient('http://api.test');
    await expect(api.me()).rejects.toMatchObject({ status: 401 } satisfies Partial<ApiError>);
  });

  it('uploads multipart with the field named file', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { id: '2', name: 'b.cs' }));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient('http://api.test', 'tok');
    await api.upload('b.cs', new Blob(['x']), 'text/plain');
    const body = fetchMock.mock.calls[0][1].body as FormData;
    expect(body.get('file')).toBeInstanceOf(Blob);
    expect((body.get('file') as File).name).toBe('b.cs');
  });
});

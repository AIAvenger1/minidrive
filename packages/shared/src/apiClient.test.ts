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

  it('trims a trailing slash off the base url', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient(' http://api.test/// ', 'tok');
    expect(api.baseUrl).toBe('http://api.test');
    await api.listFiles();
    expect(fetchMock.mock.calls[0][0]).toBe('http://api.test/files');
  });

  it('downloads content as a blob', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(new Blob(['data']), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient('http://api.test', 'tok');
    const blob = await api.download('42');
    expect(fetchMock.mock.calls[0][0]).toBe('http://api.test/files/42/content');
    expect(await blob.text()).toBe('data');
  });

  it('removes a file', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient('http://api.test', 'tok');
    await api.remove('42');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api.test/files/42');
    expect(init.method).toBe('DELETE');
  });

  it('registers with username and password', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { accessToken: 't', user: { id: '1', username: 'bohdan' } }));
    vi.stubGlobal('fetch', fetchMock);
    const api = new ApiClient('http://api.test');
    const result = await api.register('bohdan', 'secret');
    expect(result.accessToken).toBe('t');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api.test/auth/register');
    expect(JSON.parse(init.body as string)).toEqual({ username: 'bohdan', password: 'secret' });
  });

  it('resolves to undefined on a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const api = new ApiClient('http://api.test', 'tok');
    await expect(api.remove('1')).resolves.toBeUndefined();
  });

  it('joins an array message from the error body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(400, { message: ['name is required', 'name is too long'] })));
    const api = new ApiClient('http://api.test');
    await expect(api.me()).rejects.toMatchObject({
      status: 400,
      message: 'name is required; name is too long',
    } satisfies Partial<ApiError>);
  });
});

import type { AuthResponseDto, FileDto, UserDto } from './types';

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

export class ApiClient {
  private token: string | null;

  constructor(readonly baseUrl: string, token: string | null = null) {
    this.token = token;
  }

  setToken(token: string | null): void {
    this.token = token;
  }

  register(username: string, password: string): Promise<AuthResponseDto> {
    return this.json('POST', '/auth/register', { username, password });
  }

  login(username: string, password: string): Promise<AuthResponseDto> {
    return this.json('POST', '/auth/login', { username, password });
  }

  me(): Promise<UserDto> {
    return this.json('GET', '/auth/me');
  }

  listFiles(): Promise<FileDto[]> {
    return this.json('GET', '/files');
  }

  async upload(name: string, data: Blob | Uint8Array<ArrayBuffer>, mimeType = 'application/octet-stream'): Promise<FileDto> {
    const form = new FormData();
    let blob: Blob;
    if (data instanceof Blob) {
      blob = data;
    } else {
      blob = new Blob([data], { type: mimeType });
    }
    form.append('file', new File([blob], name, { type: blob.type || mimeType }));
    const res = await fetch(`${this.baseUrl}/files`, { method: 'POST', headers: this.authHeaders(), body: form });
    return this.handle(res);
  }

  async download(id: string): Promise<Blob> {
    const res = await fetch(`${this.baseUrl}/files/${id}/content`, { headers: this.authHeaders() });
    if (!res.ok) throw await this.error(res);
    return res.blob();
  }

  async remove(id: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/files/${id}`, { method: 'DELETE', headers: this.authHeaders() });
    if (!res.ok) throw await this.error(res);
  }

  private async json<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { ...this.authHeaders() };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return this.handle<T>(res);
  }

  private authHeaders(): Record<string, string> {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }

  private async handle<T>(res: Response): Promise<T> {
    if (!res.ok) throw await this.error(res);
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  private async error(res: Response): Promise<ApiError> {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.message === 'string') message = body.message;
      else if (Array.isArray(body?.message)) message = body.message.join('; ');
    } catch {}
    return new ApiError(res.status, message);
  }
}

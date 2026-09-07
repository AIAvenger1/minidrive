# MiniDrive Stage 2 — API server and desktop client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working NestJS + PostgreSQL + MinIO file server in Docker and an Electron desktop client that logs in, lists files with attributes, sorts by name, filters `.cpp`/`.png`, previews `.cs`/`.jpg`, uploads (button and drag-and-drop), downloads (button and drag-out), deletes, and synchronizes a bound local folder — with unit tests and the Stage 2 report.

**Architecture:** Yarn 4 workspaces monorepo. `packages/shared` holds types, the preview class hierarchy, the fetch-based `ApiClient`, the pure `DriveViewModel` and the pure functions (`sortByName`, `filterByType`, `previewKindOf`, `toggleColumn`, `computeSyncPlan`) that both clients use. `packages/ui` holds the plain-React components (`FileTable`, `SortControl`, `FilterControl`, `ColumnToggle`, `UploadDropzone`, `PreviewPanel`) and the `useDrive` hook, with no Electron or Next.js imports, so Stage 3 (Next.js) reuses them unchanged via `transpilePackages`. `apps/api` is a NestJS 11 REST API (Prisma/PostgreSQL for metadata, MinIO via the S3 SDK for bytes, JWT auth). `apps/desktop` is an Electron + React + Vite app: renderer UI reuses shared logic, main process owns the file system (folder scan, sync, watcher, drag-out).

**Tech Stack:** Node 22, TypeScript 5, Yarn 4 workspaces (corepack, node-modules linker), NestJS 11, Prisma 6, PostgreSQL 16, MinIO, `@aws-sdk/client-s3`, `@nestjs/jwt` + `passport-jwt`, bcrypt, Jest (API), Vitest (shared, desktop), Electron (electron-vite react-ts template), electron-store, chokidar, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-07-minidrive-design.md` (names are final; §3 architecture, §3.2 REST API and errors, §3.3 shared functions, §4 behaviours, §7 testing).

## Global Constraints

- Names from the spec are used verbatim: `User`, `FileEntry`, `FileDto`, `AuthResponseDto`, `FilesService.upsert`, `StorageService.putObject/getObject/deleteObject`, `SyncEngine.scan/synchronize/startWatching/stopWatching`, `LocalFolderScanner`, `FolderWatcher`, `DragOutHandler`, `PreloadBridge` (`window.minidrive`), `DriveViewModel`, `FileTable`, `ColumnToggle`, `SortControl`, `FilterControl`, `PreviewPanel`, `UploadDropzone`, `SyncPanel`.
- REST routes exactly: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /files`, `POST /files` (multipart field `file`), `GET /files/:id/content`, `DELETE /files/:id`. Errors: 401 unauthorized, 404 file not in caller's space, 409 username taken, 413 file too large (50 MB), 400 validation.
- Overwrite rule: uploading a name that already exists in the owner's space keeps the same `FileEntry` row and `storageKey`, replaces bytes, sets `updatedAt = now`, `modifiedById = caller`.
- Storage key: `users/{ownerId}/{fileEntry.id}` in bucket `minidrive`. Unique constraint `(ownerId, name)`.
- Sync rules (§4.2): only local → upload; only remote → download; both with same size and |mtime − updatedAt| ≤ 2000 ms → skip; otherwise newest wins; deletions never propagate; after a download set the local mtime to `updatedAt`.
- Preview: text-like extensions → `'text'`, raster images → `'image'`, else `'none'` (lists in Task 3). `.cs` and `.jpg` are the mandatory tested cases.
- Filter `'cpp-png'` keeps extensions `cpp` and `png`, case-insensitive. Sort is stable, case-insensitive, `localeCompare` with `numeric: true`. Column `name` can never be hidden.
- **Code style: no comments in code. No docstrings. No "generated" markers. Clear names instead.** Commit messages are short, plain, lowercase after the type prefix.
- JWT HS256, 24 h, header `Authorization: Bearer <token>`. Passwords hashed with bcrypt (10 rounds).
- Package manager: Yarn 4.9.1 via corepack (`"packageManager": "yarn@4.9.1"` in the root `package.json`, `.yarnrc.yml` with `nodeLinker: node-modules`; never PnP). Node 22. All packages are private. Workspace dependencies use the `workspace:*` protocol.
- `packages/ui` and `packages/shared` must not import from `electron`, `window.minidrive`, `next/*` or Node built-ins; anything platform-specific is passed in as props or constructor arguments.
- Deviation from spec §7: the API end-to-end check is `tools/api-smoke.sh` against the running Docker stack instead of a supertest e2e test; unit tests cover the services.

---

## Part A — Monorepo and shared package

### Task 1: Monorepo scaffold and first commit

**Files:**
- Create: `package.json`, `.yarnrc.yml`, `tsconfig.base.json`, `.editorconfig`, `.nvmrc`, `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Produces: workspace globs `packages/*`, `apps/*`; root scripts `build`, `test`, `stack:up`, `stack:down`.

- [ ] **Step 1: Write root package.json**

```json
{
  "name": "minidrive",
  "private": true,
  "packageManager": "yarn@4.9.1",
  "workspaces": ["packages/*", "apps/*"],
  "engines": { "node": ">=22" },
  "scripts": {
    "build": "yarn workspaces foreach -A --topological-dev run build",
    "test": "yarn workspaces foreach -A run test",
    "stack:up": "docker compose -f docker/compose.yml up -d --build --wait",
    "stack:down": "docker compose -f docker/compose.yml down",
    "stack:reset": "docker compose -f docker/compose.yml down -v"
  }
}
```

`.yarnrc.yml`:
```yaml
nodeLinker: node-modules
```

- [ ] **Step 2: Write tsconfig.base.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "sourceMap": true
  }
}
```

- [ ] **Step 3: Write .editorconfig, .nvmrc, README.md**

`.editorconfig`:
```
root = true
[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
insert_final_newline = true
trim_trailing_whitespace = true
```

`.nvmrc`:
```
22
```

`README.md`:
```markdown
# MiniDrive

Клієнт для віддаленої папки з файлами (курс «Інформаційні технології», варіант 4-6).

- `apps/api` — REST-сервер (NestJS, PostgreSQL, MinIO)
- `apps/desktop` — десктоп-клієнт (Electron)
- `apps/web` — веб-клієнт (Next.js, етап 3)
- `packages/shared` — спільні типи та логіка
- `docs/` — специфікація, UML, звіти

## Запуск

```bash
corepack enable
yarn install
cp docker/.env.example docker/.env
yarn stack:up
yarn workspace @minidrive/desktop dev
```
```

- [ ] **Step 4: Extend .gitignore**

Append:
```
dist/
out/
.env
.yarn/
*.tsbuildinfo
docs/reports/*.docx
docs/reports/*.pdf
```

- [ ] **Step 5: Install and commit**

Run: `corepack enable && yarn install && git add -A && git commit -m "chore: monorepo scaffold, stage 1 docs and uml"`
Expected: commit created on `main`, `yarn.lock` present, `node_modules/` (not `.pnp.cjs`) created.

---

### Task 2: Shared package — types, sortByName, filterByType

**Files:**
- Create: `packages/shared/package.json`, `packages/shared/tsconfig.json`, `packages/shared/tsconfig.build.json`, `packages/shared/vitest.config.ts`, `packages/shared/src/types.ts`, `packages/shared/src/fileList.ts`, `packages/shared/src/index.ts`
- Test: `packages/shared/src/fileList.test.ts`

**Interfaces:**
- Produces:
  - `type FileDto = { id: string; name: string; extension: string; size: number; createdAt: string; updatedAt: string; uploadedBy: string; modifiedBy: string }`
  - `type SortOrder = 'asc' | 'desc'`, `type FileFilter = 'all' | 'cpp-png'`
  - `type ColumnKey = 'name' | 'size' | 'extension' | 'createdAt' | 'updatedAt' | 'uploadedBy' | 'modifiedBy'`, `type ColumnVisibility = Record<ColumnKey, boolean>`
  - `type PreviewKind = 'text' | 'image' | 'none'`
  - `type LocalFileInfo = { name: string; size: number; mtime: number }` (mtime in ms)
  - `type SyncActionKind = 'upload' | 'download' | 'skip'`, `type SyncAction = { kind: SyncActionKind; name: string; reason: string }`, `type SyncPlan = { uploads: SyncAction[]; downloads: SyncAction[]; skipped: SyncAction[] }`, `type SyncReport = { uploaded: number; downloaded: number; skipped: number; failed: number; errors: string[] }`
  - `sortByName(files: FileDto[], order: SortOrder): FileDto[]`, `filterByType(files: FileDto[], filter: FileFilter): FileDto[]`, `extensionOf(name: string): string`

- [ ] **Step 1: Package files**

`packages/shared/package.json`:
```json
{
  "name": "@minidrive/shared",
  "version": "0.1.0",
  "private": true,
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc -p tsconfig.build.json",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "vitest": "^3.0.0"
  }
}
```

`packages/shared/tsconfig.json`:
```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": { "outDir": "dist", "rootDir": "src", "lib": ["ES2022", "DOM"] },
  "include": ["src"]
}
```

`packages/shared/tsconfig.build.json`:
```json
{
  "extends": "./tsconfig.json",
  "exclude": ["src/**/*.test.ts"]
}
```

`packages/shared/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: { include: ['src/**/*.test.ts'] },
});
```

- [ ] **Step 2: Write types.ts**

```ts
export type FileDto = {
  id: string;
  name: string;
  extension: string;
  size: number;
  createdAt: string;
  updatedAt: string;
  uploadedBy: string;
  modifiedBy: string;
};

export type UserDto = { id: string; username: string };
export type AuthResponseDto = { accessToken: string; user: UserDto };

export type SortOrder = 'asc' | 'desc';
export type FileFilter = 'all' | 'cpp-png';

export type ColumnKey = 'name' | 'size' | 'extension' | 'createdAt' | 'updatedAt' | 'uploadedBy' | 'modifiedBy';
export type ColumnVisibility = Record<ColumnKey, boolean>;

export type PreviewKind = 'text' | 'image' | 'none';

export type LocalFileInfo = { name: string; size: number; mtime: number };

export type SyncActionKind = 'upload' | 'download' | 'skip';
export type SyncAction = { kind: SyncActionKind; name: string; reason: string };
export type SyncPlan = { uploads: SyncAction[]; downloads: SyncAction[]; skipped: SyncAction[] };
export type SyncReport = { uploaded: number; downloaded: number; skipped: number; failed: number; errors: string[] };
```

- [ ] **Step 3: Write the failing tests**

`packages/shared/src/fileList.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { extensionOf, filterByType, sortByName } from './fileList';
import type { FileDto } from './types';

const file = (name: string, i = 0): FileDto => ({
  id: `id-${name}-${i}`,
  name,
  extension: extensionOf(name),
  size: 10,
  createdAt: '2026-09-01T10:00:00.000Z',
  updatedAt: '2026-09-01T10:00:00.000Z',
  uploadedBy: 'bohdan',
  modifiedBy: 'bohdan',
});

describe('sortByName', () => {
  const files = [file('report.cs'), file('Alpha.png'), file('beta.cpp'), file('file10.txt'), file('file2.txt')];

  it('sorts ascending, case-insensitively and numerically', () => {
    expect(sortByName(files, 'asc').map((f) => f.name)).toEqual([
      'Alpha.png', 'beta.cpp', 'file2.txt', 'file10.txt', 'report.cs',
    ]);
  });

  it('sorts descending', () => {
    expect(sortByName(files, 'desc').map((f) => f.name)).toEqual([
      'report.cs', 'file10.txt', 'file2.txt', 'beta.cpp', 'Alpha.png',
    ]);
  });

  it('does not mutate the input and is stable for equal names', () => {
    const dup = [file('same.txt', 1), file('same.txt', 2)];
    const sorted = sortByName(dup, 'asc');
    expect(sorted.map((f) => f.id)).toEqual(['id-same.txt-1', 'id-same.txt-2']);
    expect(dup.map((f) => f.id)).toEqual(['id-same.txt-1', 'id-same.txt-2']);
    expect(sorted).not.toBe(dup);
  });
});

describe('filterByType', () => {
  const files = [file('main.cpp'), file('logo.PNG'), file('report.cs'), file('photo.jpg'), file('notes')];

  it('returns everything for "all"', () => {
    expect(filterByType(files, 'all')).toHaveLength(5);
  });

  it('keeps only .cpp and .png for "cpp-png", case-insensitively', () => {
    expect(filterByType(files, 'cpp-png').map((f) => f.name)).toEqual(['main.cpp', 'logo.PNG']);
  });
});

describe('extensionOf', () => {
  it('returns the lower-cased extension without the dot', () => {
    expect(extensionOf('Photo.JPG')).toBe('jpg');
    expect(extensionOf('archive.tar.gz')).toBe('gz');
    expect(extensionOf('README')).toBe('');
    expect(extensionOf('.env')).toBe('');
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `yarn install && yarn workspace @minidrive/shared` test
Expected: FAIL — cannot resolve `./fileList`.

- [ ] **Step 5: Implement fileList.ts and index.ts**

`packages/shared/src/fileList.ts`:
```ts
import type { FileDto, FileFilter, SortOrder } from './types';

const VARIANT_FILTER_EXTENSIONS = new Set(['cpp', 'png']);

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  if (dot <= 0) return '';
  return name.slice(dot + 1).toLowerCase();
}

export function sortByName(files: FileDto[], order: SortOrder): FileDto[] {
  const direction = order === 'asc' ? 1 : -1;
  return [...files].sort(
    (a, b) => direction * a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }),
  );
}

export function filterByType(files: FileDto[], filter: FileFilter): FileDto[] {
  if (filter === 'all') return files;
  return files.filter((f) => VARIANT_FILTER_EXTENSIONS.has(extensionOf(f.name)));
}
```

`packages/shared/src/index.ts`:
```ts
export * from './types';
export * from './fileList';
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `yarn workspace @minidrive/shared` test
Expected: PASS (7 tests).

- [ ] **Step 7: Commit**

```bash
git add packages/shared yarn.lock
git commit -m "feat(shared): types, sortByName and filterByType with tests"
```

---

### Task 3: Shared package — preview kind and preview classes

**Files:**
- Create: `packages/shared/src/preview.ts`
- Modify: `packages/shared/src/index.ts`
- Test: `packages/shared/src/preview.test.ts`

**Interfaces:**
- Produces: `previewKindOf(name: string): PreviewKind`; `abstract class FilePreview { constructor(readonly entry: FileDto); abstract readonly kind: PreviewKind; canRender(ext: string): boolean; abstract render(content: Blob): Promise<PreviewResult> }`; `class TextPreview`, `class ImagePreview`; `type PreviewResult = { kind: 'text'; text: string } | { kind: 'image'; url: string }`; `createPreview(entry: FileDto): FilePreview | null`.
- `ImagePreview.render` uses `URL.createObjectURL`, available in browsers and Electron renderer; tests mock it.

- [ ] **Step 1: Write the failing tests**

`packages/shared/src/preview.test.ts`:
```ts
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `yarn workspace @minidrive/shared` test
Expected: FAIL — cannot resolve `./preview`.

- [ ] **Step 3: Implement preview.ts**

```ts
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
```

Add to `index.ts`: `export * from './preview';`

- [ ] **Step 4: Run tests to verify they pass**

Run: `yarn workspace @minidrive/shared` test
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/shared
git commit -m "feat(shared): preview kind detection and preview classes"
```

---

### Task 4: Shared package — column visibility

**Files:**
- Create: `packages/shared/src/columns.ts`
- Modify: `packages/shared/src/index.ts`
- Test: `packages/shared/src/columns.test.ts`

**Interfaces:**
- Produces: `COLUMN_KEYS: ColumnKey[]` (order used by the table), `DEFAULT_COLUMNS: ColumnVisibility` (all true), `toggleColumn(v: ColumnVisibility, key: ColumnKey): ColumnVisibility`, `hideAllButName(): ColumnVisibility`, `COLUMN_LABELS: Record<ColumnKey, string>` (Ukrainian labels for the UI).

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, expect, it } from 'vitest';
import { COLUMN_KEYS, DEFAULT_COLUMNS, hideAllButName, toggleColumn } from './columns';

describe('toggleColumn', () => {
  it('flips a column and returns a new object', () => {
    const next = toggleColumn(DEFAULT_COLUMNS, 'createdAt');
    expect(next.createdAt).toBe(false);
    expect(DEFAULT_COLUMNS.createdAt).toBe(true);
    expect(toggleColumn(next, 'createdAt').createdAt).toBe(true);
  });

  it('never hides the name column', () => {
    expect(toggleColumn(DEFAULT_COLUMNS, 'name').name).toBe(true);
  });

  it('hideAllButName keeps only the name', () => {
    const v = hideAllButName();
    expect(v.name).toBe(true);
    expect(COLUMN_KEYS.filter((k) => k !== 'name').every((k) => v[k] === false)).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `yarn workspace @minidrive/shared` test
Expected: FAIL — cannot resolve `./columns`.

- [ ] **Step 3: Implement columns.ts**

```ts
import type { ColumnKey, ColumnVisibility } from './types';

export const COLUMN_KEYS: ColumnKey[] = ['name', 'extension', 'size', 'createdAt', 'updatedAt', 'uploadedBy', 'modifiedBy'];

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  name: 'Назва',
  extension: 'Тип',
  size: 'Розмір',
  createdAt: 'Створено',
  updatedAt: 'Змінено',
  uploadedBy: 'Завантажив',
  modifiedBy: 'Редагував',
};

export const DEFAULT_COLUMNS: ColumnVisibility = {
  name: true, extension: true, size: true, createdAt: true, updatedAt: true, uploadedBy: true, modifiedBy: true,
};

export function toggleColumn(visibility: ColumnVisibility, key: ColumnKey): ColumnVisibility {
  if (key === 'name') return { ...visibility, name: true };
  return { ...visibility, [key]: !visibility[key] };
}

export function hideAllButName(): ColumnVisibility {
  return { ...DEFAULT_COLUMNS, extension: false, size: false, createdAt: false, updatedAt: false, uploadedBy: false, modifiedBy: false };
}
```

Add to `index.ts`: `export * from './columns';`

- [ ] **Step 4: Run tests, then commit**

Run: `yarn workspace @minidrive/shared` test → PASS.

```bash
git add packages/shared
git commit -m "feat(shared): column visibility helpers"
```

---

### Task 5: Shared package — computeSyncPlan and ApiClient

**Files:**
- Create: `packages/shared/src/sync.ts`, `packages/shared/src/apiClient.ts`
- Modify: `packages/shared/src/index.ts`
- Test: `packages/shared/src/sync.test.ts`, `packages/shared/src/apiClient.test.ts`

**Interfaces:**
- Produces: `computeSyncPlan(local: LocalFileInfo[], remote: FileDto[]): SyncPlan` with `SKEW_MS = 2000`.
- Produces: `class ApiClient { constructor(baseUrl: string, token?: string | null); setToken(t: string | null); register(username, password): Promise<AuthResponseDto>; login(username, password): Promise<AuthResponseDto>; me(): Promise<UserDto>; listFiles(): Promise<FileDto[]>; upload(name: string, data: Blob | Uint8Array, mimeType?: string): Promise<FileDto>; download(id: string): Promise<Blob>; remove(id: string): Promise<void> }` and `class ApiError extends Error { status: number }`. Uses global `fetch`/`FormData`/`Blob` (Node 22, browsers, Electron).

- [ ] **Step 1: Write the failing sync tests**

`packages/shared/src/sync.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { computeSyncPlan } from './sync';
import type { FileDto, LocalFileInfo } from './types';

const t0 = Date.parse('2026-09-01T10:00:00.000Z');
const remote = (name: string, size: number, updatedAtMs: number): FileDto => ({
  id: `r-${name}`, name, extension: '', size, createdAt: '', updatedAt: new Date(updatedAtMs).toISOString(), uploadedBy: 'a', modifiedBy: 'a',
});
const local = (name: string, size: number, mtime: number): LocalFileInfo => ({ name, size, mtime });

describe('computeSyncPlan', () => {
  it('uploads files that exist only locally', () => {
    const plan = computeSyncPlan([local('a.txt', 5, t0)], []);
    expect(plan.uploads.map((a) => a.name)).toEqual(['a.txt']);
    expect(plan.downloads).toEqual([]);
  });

  it('downloads files that exist only remotely', () => {
    const plan = computeSyncPlan([], [remote('b.png', 5, t0)]);
    expect(plan.downloads.map((a) => a.name)).toEqual(['b.png']);
  });

  it('skips identical files within the clock skew', () => {
    const plan = computeSyncPlan([local('c.cs', 7, t0 + 1500)], [remote('c.cs', 7, t0)]);
    expect(plan.skipped.map((a) => a.name)).toEqual(['c.cs']);
  });

  it('uploads when the local copy is newer', () => {
    const plan = computeSyncPlan([local('d.cpp', 9, t0 + 60_000)], [remote('d.cpp', 8, t0)]);
    expect(plan.uploads[0]).toMatchObject({ name: 'd.cpp', kind: 'upload' });
  });

  it('downloads when the remote copy is newer', () => {
    const plan = computeSyncPlan([local('e.jpg', 9, t0)], [remote('e.jpg', 8, t0 + 60_000)]);
    expect(plan.downloads[0]).toMatchObject({ name: 'e.jpg', kind: 'download' });
  });

  it('treats a size difference within the skew window as a change', () => {
    const plan = computeSyncPlan([local('f.txt', 10, t0 + 500)], [remote('f.txt', 11, t0)]);
    expect(plan.uploads.map((a) => a.name)).toEqual(['f.txt']);
  });
});
```

- [ ] **Step 2: Write the failing ApiClient test**

`packages/shared/src/apiClient.test.ts`:
```ts
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `yarn workspace @minidrive/shared` test
Expected: FAIL — modules not found.

- [ ] **Step 4: Implement sync.ts**

```ts
import type { FileDto, LocalFileInfo, SyncAction, SyncPlan } from './types';

export const SKEW_MS = 2000;

export function computeSyncPlan(local: LocalFileInfo[], remote: FileDto[]): SyncPlan {
  const plan: SyncPlan = { uploads: [], downloads: [], skipped: [] };
  const remoteByName = new Map(remote.map((r) => [r.name, r]));
  const localByName = new Map(local.map((l) => [l.name, l]));

  for (const l of local) {
    const r = remoteByName.get(l.name);
    if (!r) {
      plan.uploads.push(action('upload', l.name, 'only local'));
      continue;
    }
    const remoteTime = Date.parse(r.updatedAt);
    const sameSize = l.size === r.size;
    const closeInTime = Math.abs(l.mtime - remoteTime) <= SKEW_MS;
    if (sameSize && closeInTime) {
      plan.skipped.push(action('skip', l.name, 'unchanged'));
    } else if (l.mtime >= remoteTime) {
      plan.uploads.push(action('upload', l.name, 'local newer'));
    } else {
      plan.downloads.push(action('download', l.name, 'remote newer'));
    }
  }

  for (const r of remote) {
    if (!localByName.has(r.name)) {
      plan.downloads.push(action('download', r.name, 'only remote'));
    }
  }
  return plan;
}

function action(kind: SyncAction['kind'], name: string, reason: string): SyncAction {
  return { kind, name, reason };
}
```

- [ ] **Step 5: Implement apiClient.ts**

```ts
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

  async upload(name: string, data: Blob | Uint8Array, mimeType = 'application/octet-stream'): Promise<FileDto> {
    const form = new FormData();
    const blob = data instanceof Blob ? data : new Blob([data], { type: mimeType });
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
```

Add to `index.ts`: `export * from './sync';` and `export * from './apiClient';`

- [ ] **Step 6: Run tests, build, commit**

Run: `yarn workspace @minidrive/shared test && yarn workspace @minidrive/shared` build
Expected: PASS; `packages/shared/dist/index.js` and `.d.ts` exist.

```bash
git add packages/shared
git commit -m "feat(shared): sync plan and fetch api client"
```

---

## Part B — API server

### Task 6: NestJS scaffold, environment, Prisma schema, Docker Compose

**Files:**
- Create: `apps/api/` (Nest CLI), `apps/api/prisma/schema.prisma`, `apps/api/src/config.ts`, `docker/compose.yml`, `docker/.env.example`, `apps/api/.env.example`
- Modify: `apps/api/package.json`, `apps/api/tsconfig.json`, `apps/api/src/main.ts`, `apps/api/src/app.module.ts`

**Interfaces:**
- Produces: `loadConfig(): AppConfig` with `{ port: number; databaseUrl: string; jwtSecret: string; s3: { endpoint: string; accessKey: string; secretKey: string; bucket: string; region: string }; corsOrigins: string[]; maxFileBytes: number }`.
- Produces: Prisma models `User` and `FileEntry` (below). Compose services `postgres` (5432), `minio` (9000 API, 9001 console), `api` (3000).

- [ ] **Step 1: Scaffold with the Nest CLI**

Run from repo root:
```bash
npx --yes @nestjs/cli@11 new api --directory apps/api --package-manager yarn --skip-git --strict
rm -rf apps/api/node_modules apps/api/yarn.lock apps/api/.yarnrc.yml
```
Then edit `apps/api/package.json`: set `"name": "@minidrive/api"`, `"private": true`, keep the CLI scripts. Delete `apps/api/src/app.controller.ts`, `app.controller.spec.ts`, `app.service.ts`.

- [ ] **Step 2: Add dependencies**

```bash
yarn workspace @minidrive/api add @nestjs/config @nestjs/jwt @nestjs/passport passport passport-jwt bcrypt @prisma/client @aws-sdk/client-s3 @nestjs/swagger class-validator class-transformer
yarn workspace @minidrive/api add -D prisma @types/passport-jwt @types/bcrypt @types/multer
yarn workspace @minidrive/api add @minidrive/shared@workspace:*
```

- [ ] **Step 3: Prisma schema**

`apps/api/prisma/schema.prisma`:
```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id           String      @id @default(uuid())
  username     String      @unique
  passwordHash String
  createdAt    DateTime    @default(now())
  ownedFiles   FileEntry[] @relation("owner")
  uploaded     FileEntry[] @relation("uploadedBy")
  modified     FileEntry[] @relation("modifiedBy")
}

model FileEntry {
  id           String   @id @default(uuid())
  ownerId      String
  name         String
  extension    String
  size         Int
  storageKey   String
  createdAt    DateTime @default(now())
  updatedAt    DateTime @default(now())
  uploadedById String
  modifiedById String
  owner        User     @relation("owner", fields: [ownerId], references: [id], onDelete: Cascade)
  uploadedBy   User     @relation("uploadedBy", fields: [uploadedById], references: [id])
  modifiedBy   User     @relation("modifiedBy", fields: [modifiedById], references: [id])

  @@unique([ownerId, name])
}
```

- [ ] **Step 4: Config and env files**

`apps/api/src/config.ts`:
```ts
export type AppConfig = {
  port: number;
  databaseUrl: string;
  jwtSecret: string;
  s3: { endpoint: string; accessKey: string; secretKey: string; bucket: string; region: string };
  corsOrigins: string[];
  maxFileBytes: number;
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const required = (key: string): string => {
    const value = env[key];
    if (!value) throw new Error(`Missing environment variable ${key}`);
    return value;
  };
  return {
    port: Number(env.PORT ?? 3000),
    databaseUrl: required('DATABASE_URL'),
    jwtSecret: required('JWT_SECRET'),
    s3: {
      endpoint: required('S3_ENDPOINT'),
      accessKey: required('S3_ACCESS_KEY'),
      secretKey: required('S3_SECRET_KEY'),
      bucket: env.S3_BUCKET ?? 'minidrive',
      region: env.S3_REGION ?? 'us-east-1',
    },
    corsOrigins: (env.CORS_ORIGINS ?? '*').split(',').map((s) => s.trim()).filter(Boolean),
    maxFileBytes: Number(env.MAX_FILE_MB ?? 50) * 1024 * 1024,
  };
}
```

`apps/api/.env.example` (local run outside Docker):
```
PORT=3000
DATABASE_URL=postgresql://minidrive:minidrive@localhost:5432/minidrive
JWT_SECRET=change-me-in-production
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minidrive
S3_SECRET_KEY=minidrive123
S3_BUCKET=minidrive
CORS_ORIGINS=*
MAX_FILE_MB=50
```

`docker/.env.example`:
```
POSTGRES_USER=minidrive
POSTGRES_PASSWORD=minidrive
POSTGRES_DB=minidrive
MINIO_ROOT_USER=minidrive
MINIO_ROOT_PASSWORD=minidrive123
JWT_SECRET=change-me-in-production
CORS_ORIGINS=*
API_PORT=3000
```

`docker/compose.yml`:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9000/minio/health/live || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: ..
      dockerfile: docker/api.Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      PORT: 3000
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      JWT_SECRET: ${JWT_SECRET}
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: ${MINIO_ROOT_USER}
      S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      S3_BUCKET: minidrive
      CORS_ORIGINS: ${CORS_ORIGINS}
    ports:
      - "${API_PORT}:3000"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  pgdata:
  miniodata:
```

- [ ] **Step 5: main.ts and app.module.ts**

`apps/api/src/main.ts`:
```ts
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { loadConfig } from './config';

async function bootstrap() {
  const config = loadConfig();
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: config.corsOrigins.includes('*') ? true : config.corsOrigins });
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  const doc = new DocumentBuilder().setTitle('MiniDrive API').setVersion('0.1').addBearerAuth().build();
  SwaggerModule.setup('docs', app, SwaggerModule.createDocument(app, doc));
  await app.listen(config.port);
}

bootstrap();
```

`apps/api/src/app.module.ts` (modules are added in later tasks; start with the health controller):
```ts
import { Controller, Get, Module } from '@nestjs/common';

@Controller('health')
class HealthController {
  @Get()
  health() {
    return { status: 'ok' };
  }
}

@Module({ controllers: [HealthController] })
export class AppModule {}
```

- [ ] **Step 6: Generate the Prisma client and the first migration**

```bash
cp docker/.env.example docker/.env
docker compose -f docker/compose.yml up -d postgres minio --wait
cp apps/api/.env.example apps/api/.env
yarn workspace @minidrive/api prisma migrate dev --name init
yarn workspace @minidrive/api prisma generate
```
Expected: `apps/api/prisma/migrations/<timestamp>_init/migration.sql` created; tables `User`, `FileEntry` exist.

Add to `apps/api/package.json` scripts: `"prisma": "prisma"`, `"db:migrate": "prisma migrate deploy"`, and prepend `dotenv`-free loading by running the API with `node -r ./load-env.js` — simpler: add `import 'dotenv/config';` as the first line of `main.ts` and install `dotenv` (`yarn workspace @minidrive/api add dotenv`). In Docker the variables come from compose, so `dotenv` finds nothing and is harmless.

- [ ] **Step 7: Verify boot and commit**

Run: `yarn workspace @minidrive/api` start:dev then `curl -s localhost:3000/health`
Expected: `{"status":"ok"}`; Swagger at `http://localhost:3000/docs`.

```bash
git add apps/api docker yarn.lock
git commit -m "feat(api): nest scaffold, prisma schema, docker compose"
```

---

### Task 7: PrismaModule and UsersModule

**Files:**
- Create: `apps/api/src/prisma/prisma.module.ts`, `apps/api/src/prisma/prisma.service.ts`, `apps/api/src/users/users.module.ts`, `apps/api/src/users/users.service.ts`
- Test: `apps/api/src/users/users.service.spec.ts`
- Modify: `apps/api/src/app.module.ts`

**Interfaces:**
- Produces: `PrismaService extends PrismaClient` (global module). `UsersService { findByUsername(username): Promise<User | null>; findById(id): Promise<User | null>; create(username, password): Promise<User>; verify(password, hash): Promise<boolean>; hash(password): Promise<string> }`.

- [ ] **Step 1: Write the failing test**

`apps/api/src/users/users.service.spec.ts`:
```ts
import { UsersService } from './users.service';

describe('UsersService', () => {
  const prisma = { user: { findUnique: jest.fn(), create: jest.fn() } };
  const service = new UsersService(prisma as never);

  beforeEach(() => jest.clearAllMocks());

  it('hashes the password on create and never stores it in clear', async () => {
    prisma.user.create.mockImplementation(async ({ data }: { data: { username: string; passwordHash: string } }) => ({ id: 'u1', ...data }));
    const user = await service.create('bohdan', 'secret123');
    expect(user.passwordHash).not.toBe('secret123');
    expect(await service.verify('secret123', user.passwordHash)).toBe(true);
    expect(await service.verify('wrong', user.passwordHash)).toBe(false);
  });

  it('looks up by username', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 'u1', username: 'bohdan' });
    expect(await service.findByUsername('bohdan')).toMatchObject({ id: 'u1' });
    expect(prisma.user.findUnique).toHaveBeenCalledWith({ where: { username: 'bohdan' } });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `yarn workspace @minidrive/api test users.service`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`apps/api/src/prisma/prisma.service.ts`:
```ts
import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  async onModuleInit() {
    await this.$connect();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }
}
```

`apps/api/src/prisma/prisma.module.ts`:
```ts
import { Global, Module } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Global()
@Module({ providers: [PrismaService], exports: [PrismaService] })
export class PrismaModule {}
```

`apps/api/src/users/users.service.ts`:
```ts
import { Injectable } from '@nestjs/common';
import { User } from '@prisma/client';
import * as bcrypt from 'bcrypt';
import { PrismaService } from '../prisma/prisma.service';

const ROUNDS = 10;

@Injectable()
export class UsersService {
  constructor(private readonly prisma: PrismaService) {}

  findByUsername(username: string): Promise<User | null> {
    return this.prisma.user.findUnique({ where: { username } });
  }

  findById(id: string): Promise<User | null> {
    return this.prisma.user.findUnique({ where: { id } });
  }

  async create(username: string, password: string): Promise<User> {
    return this.prisma.user.create({ data: { username, passwordHash: await this.hash(password) } });
  }

  hash(password: string): Promise<string> {
    return bcrypt.hash(password, ROUNDS);
  }

  verify(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }
}
```

`apps/api/src/users/users.module.ts`:
```ts
import { Module } from '@nestjs/common';
import { UsersService } from './users.service';

@Module({ providers: [UsersService], exports: [UsersService] })
export class UsersModule {}
```

Update `app.module.ts` imports: `imports: [PrismaModule, UsersModule]` (keep `HealthController`).

- [ ] **Step 4: Run tests and commit**

Run: `yarn workspace @minidrive/api test users.service` → PASS.

```bash
git add apps/api/src
git commit -m "feat(api): prisma and users modules"
```

---

### Task 8: AuthModule — register, login, me, JWT guard

**Files:**
- Create: `apps/api/src/auth/dto.ts`, `apps/api/src/auth/auth.service.ts`, `apps/api/src/auth/auth.controller.ts`, `apps/api/src/auth/jwt.strategy.ts`, `apps/api/src/auth/jwt-auth.guard.ts`, `apps/api/src/auth/current-user.decorator.ts`, `apps/api/src/auth/auth.module.ts`
- Test: `apps/api/src/auth/auth.service.spec.ts`
- Modify: `apps/api/src/app.module.ts`

**Interfaces:**
- Produces: `RegisterDto`, `LoginDto` (`username` 3–32 chars `[a-zA-Z0-9_.-]`, `password` 6–72 chars), `AuthResponseDto`, `UserDto`.
- Produces: `AuthService { register(dto): Promise<AuthResponseDto>; login(dto): Promise<AuthResponseDto>; validateUser(username, password): Promise<User> }`; `JwtAuthGuard`; `@CurrentUser()` param decorator returning `{ id: string; username: string }`; JWT payload `{ sub: userId, username }`.

- [ ] **Step 1: Write the failing test**

`apps/api/src/auth/auth.service.spec.ts`:
```ts
import { ConflictException, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  const users = {
    findByUsername: jest.fn(),
    create: jest.fn(),
    verify: jest.fn(),
  };
  const jwt = new JwtService({ secret: 'test-secret', signOptions: { expiresIn: '24h' } });
  const service = new AuthService(users as never, jwt);

  beforeEach(() => jest.clearAllMocks());

  it('registers a new user and returns a token', async () => {
    users.findByUsername.mockResolvedValue(null);
    users.create.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    const res = await service.register({ username: 'bohdan', password: 'secret123' });
    expect(res.user).toEqual({ id: 'u1', username: 'bohdan' });
    expect(jwt.verify(res.accessToken)).toMatchObject({ sub: 'u1', username: 'bohdan' });
  });

  it('rejects a taken username with 409', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1' });
    await expect(service.register({ username: 'bohdan', password: 'secret123' })).rejects.toBeInstanceOf(ConflictException);
  });

  it('rejects a wrong password with 401', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    users.verify.mockResolvedValue(false);
    await expect(service.login({ username: 'bohdan', password: 'nope' })).rejects.toBeInstanceOf(UnauthorizedException);
  });

  it('logs in with a correct password', async () => {
    users.findByUsername.mockResolvedValue({ id: 'u1', username: 'bohdan', passwordHash: 'h' });
    users.verify.mockResolvedValue(true);
    const res = await service.login({ username: 'bohdan', password: 'secret123' });
    expect(res.accessToken).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `yarn workspace @minidrive/api test auth.service` → FAIL (module not found).

- [ ] **Step 3: Implement**

`apps/api/src/auth/dto.ts`:
```ts
import { ApiProperty } from '@nestjs/swagger';
import { IsString, Length, Matches } from 'class-validator';

export class RegisterDto {
  @ApiProperty({ example: 'bohdan' })
  @IsString()
  @Length(3, 32)
  @Matches(/^[a-zA-Z0-9_.-]+$/)
  username!: string;

  @ApiProperty({ example: 'secret123' })
  @IsString()
  @Length(6, 72)
  password!: string;
}

export class LoginDto extends RegisterDto {}

export class UserDto {
  @ApiProperty() id!: string;
  @ApiProperty() username!: string;
}

export class AuthResponseDto {
  @ApiProperty() accessToken!: string;
  @ApiProperty({ type: UserDto }) user!: UserDto;
}
```

`apps/api/src/auth/auth.service.ts`:
```ts
import { ConflictException, Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { User } from '@prisma/client';
import { UsersService } from '../users/users.service';
import { AuthResponseDto, LoginDto, RegisterDto } from './dto';

@Injectable()
export class AuthService {
  constructor(private readonly users: UsersService, private readonly jwt: JwtService) {}

  async register(dto: RegisterDto): Promise<AuthResponseDto> {
    if (await this.users.findByUsername(dto.username)) {
      throw new ConflictException('Username is already taken');
    }
    const user = await this.users.create(dto.username, dto.password);
    return this.issue(user);
  }

  async login(dto: LoginDto): Promise<AuthResponseDto> {
    const user = await this.validateUser(dto.username, dto.password);
    return this.issue(user);
  }

  async validateUser(username: string, password: string): Promise<User> {
    const user = await this.users.findByUsername(username);
    if (!user || !(await this.users.verify(password, user.passwordHash))) {
      throw new UnauthorizedException('Invalid username or password');
    }
    return user;
  }

  private issue(user: User): AuthResponseDto {
    return {
      accessToken: this.jwt.sign({ sub: user.id, username: user.username }),
      user: { id: user.id, username: user.username },
    };
  }
}
```

`apps/api/src/auth/jwt.strategy.ts`:
```ts
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { loadConfig } from '../config';

export type JwtUser = { id: string; username: string };

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({ jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(), secretOrKey: loadConfig().jwtSecret });
  }

  validate(payload: { sub: string; username: string }): JwtUser {
    return { id: payload.sub, username: payload.username };
  }
}
```

`apps/api/src/auth/jwt-auth.guard.ts`:
```ts
import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {}
```

`apps/api/src/auth/current-user.decorator.ts`:
```ts
import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { JwtUser } from './jwt.strategy';

export const CurrentUser = createParamDecorator((_: unknown, ctx: ExecutionContext): JwtUser => {
  return ctx.switchToHttp().getRequest().user;
});
```

`apps/api/src/auth/auth.controller.ts`:
```ts
import { Body, Controller, Get, HttpCode, Post, UseGuards } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { AuthService } from './auth.service';
import { CurrentUser } from './current-user.decorator';
import { AuthResponseDto, LoginDto, RegisterDto, UserDto } from './dto';
import { JwtAuthGuard } from './jwt-auth.guard';
import { JwtUser } from './jwt.strategy';

@ApiTags('auth')
@Controller('auth')
export class AuthController {
  constructor(private readonly auth: AuthService) {}

  @Post('register')
  register(@Body() dto: RegisterDto): Promise<AuthResponseDto> {
    return this.auth.register(dto);
  }

  @Post('login')
  @HttpCode(200)
  login(@Body() dto: LoginDto): Promise<AuthResponseDto> {
    return this.auth.login(dto);
  }

  @Get('me')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  me(@CurrentUser() user: JwtUser): UserDto {
    return user;
  }
}
```

`apps/api/src/auth/auth.module.ts`:
```ts
import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { loadConfig } from '../config';
import { UsersModule } from '../users/users.module';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { JwtStrategy } from './jwt.strategy';

@Module({
  imports: [
    UsersModule,
    PassportModule,
    JwtModule.register({ secret: loadConfig().jwtSecret, signOptions: { expiresIn: '24h' } }),
  ],
  controllers: [AuthController],
  providers: [AuthService, JwtStrategy],
  exports: [AuthService],
})
export class AuthModule {}
```

Add `AuthModule` to `app.module.ts` imports.

- [ ] **Step 4: Run tests, smoke the endpoints, commit**

Run: `yarn workspace @minidrive/api test auth.service` → PASS. Start the API and run:
```bash
curl -s -X POST localhost:3000/auth/register -H 'content-type: application/json' -d '{"username":"bohdan","password":"secret123"}'
curl -s -X POST localhost:3000/auth/login -H 'content-type: application/json' -d '{"username":"bohdan","password":"secret123"}'
```
Expected: both return `{"accessToken":"...","user":{"id":"...","username":"bohdan"}}`; a second register returns 409.

```bash
git add apps/api/src
git commit -m "feat(api): auth module with jwt"
```

---

### Task 9: StorageModule — MinIO via S3 SDK

**Files:**
- Create: `apps/api/src/storage/storage.service.ts`, `apps/api/src/storage/storage.module.ts`
- Test: `apps/api/src/storage/storage.service.spec.ts`
- Modify: `apps/api/src/app.module.ts`

**Interfaces:**
- Produces: `StorageService { onModuleInit(): ensures the bucket exists; putObject(key: string, body: Buffer, mimeType: string): Promise<void>; getObject(key: string): Promise<{ stream: Readable; mimeType: string; size?: number }>; deleteObject(key: string): Promise<void> }`.

- [ ] **Step 1: Write the failing test**

```ts
import { StorageService } from './storage.service';

describe('StorageService', () => {
  it('sends put, get and delete commands with the configured bucket', async () => {
    const send = jest.fn().mockResolvedValue({ Body: 'stream', ContentType: 'text/plain', ContentLength: 3 });
    const service = new StorageService({ send } as never, 'minidrive');
    await service.putObject('users/u1/f1', Buffer.from('abc'), 'text/plain');
    const got = await service.getObject('users/u1/f1');
    await service.deleteObject('users/u1/f1');
    expect(send).toHaveBeenCalledTimes(3);
    expect(send.mock.calls[0][0].input).toMatchObject({ Bucket: 'minidrive', Key: 'users/u1/f1', ContentType: 'text/plain' });
    expect(got).toMatchObject({ mimeType: 'text/plain', size: 3 });
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `yarn workspace @minidrive/api test storage.service` → FAIL.

- [ ] **Step 3: Implement**

`apps/api/src/storage/storage.service.ts`:
```ts
import { Injectable, OnModuleInit } from '@nestjs/common';
import {
  CreateBucketCommand, DeleteObjectCommand, GetObjectCommand, HeadBucketCommand, PutObjectCommand, S3Client,
} from '@aws-sdk/client-s3';
import { Readable } from 'stream';
import { loadConfig } from '../config';

@Injectable()
export class StorageService implements OnModuleInit {
  constructor(private readonly s3: S3Client, private readonly bucket: string) {}

  static fromEnv(): StorageService {
    const { s3 } = loadConfig();
    const client = new S3Client({
      endpoint: s3.endpoint,
      region: s3.region,
      forcePathStyle: true,
      credentials: { accessKeyId: s3.accessKey, secretAccessKey: s3.secretKey },
    });
    return new StorageService(client, s3.bucket);
  }

  async onModuleInit() {
    try {
      await this.s3.send(new HeadBucketCommand({ Bucket: this.bucket }));
    } catch {
      await this.s3.send(new CreateBucketCommand({ Bucket: this.bucket }));
    }
  }

  async putObject(key: string, body: Buffer, mimeType: string): Promise<void> {
    await this.s3.send(new PutObjectCommand({ Bucket: this.bucket, Key: key, Body: body, ContentType: mimeType }));
  }

  async getObject(key: string): Promise<{ stream: Readable; mimeType: string; size?: number }> {
    const res = await this.s3.send(new GetObjectCommand({ Bucket: this.bucket, Key: key }));
    return { stream: res.Body as Readable, mimeType: res.ContentType ?? 'application/octet-stream', size: res.ContentLength };
  }

  async deleteObject(key: string): Promise<void> {
    await this.s3.send(new DeleteObjectCommand({ Bucket: this.bucket, Key: key }));
  }
}
```

`apps/api/src/storage/storage.module.ts`:
```ts
import { Module } from '@nestjs/common';
import { StorageService } from './storage.service';

@Module({
  providers: [{ provide: StorageService, useFactory: () => StorageService.fromEnv() }],
  exports: [StorageService],
})
export class StorageModule {}
```

Add `StorageModule` to `app.module.ts` imports.

- [ ] **Step 4: Test and commit**

Run: `yarn workspace @minidrive/api test storage.service` → PASS. Start the API with MinIO running and check the bucket appears in the MinIO console (`http://localhost:9001`, login `minidrive` / `minidrive123`).

```bash
git add apps/api/src
git commit -m "feat(api): storage module over minio"
```

---

### Task 10: FilesModule — list, upload (upsert), download, delete

**Files:**
- Create: `apps/api/src/files/files.service.ts`, `apps/api/src/files/files.controller.ts`, `apps/api/src/files/files.module.ts`, `apps/api/src/files/file.dto.ts`
- Test: `apps/api/src/files/files.service.spec.ts`
- Modify: `apps/api/src/app.module.ts`

**Interfaces:**
- Produces: `FilesService { listFor(ownerId): Promise<FileDto[]>; upsert(owner: JwtUser, file: { originalname: string; buffer: Buffer; mimetype: string; size: number }): Promise<FileDto>; getContent(ownerId, id): Promise<{ stream: Readable; mimeType: string; size?: number; name: string }>; delete(ownerId, id): Promise<void> }`. `FileDto` shape matches `@minidrive/shared` (`createdAt`/`updatedAt` ISO strings, `uploadedBy`/`modifiedBy` usernames).

- [ ] **Step 1: Write the failing test (overwrite semantics)**

`apps/api/src/files/files.service.spec.ts`:
```ts
import { NotFoundException } from '@nestjs/common';
import { FilesService } from './files.service';

const owner = { id: 'u1', username: 'bohdan' };
const editor = { id: 'u2', username: 'olena' };
const existing = {
  id: 'f1', ownerId: 'u1', name: 'report.cs', extension: 'cs', size: 3, storageKey: 'users/u1/f1',
  createdAt: new Date('2026-09-01T10:00:00Z'), updatedAt: new Date('2026-09-01T10:00:00Z'),
  uploadedById: 'u1', modifiedById: 'u1',
  uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' },
};

describe('FilesService.upsert', () => {
  const prisma = { fileEntry: { findUnique: jest.fn(), findMany: jest.fn(), create: jest.fn(), update: jest.fn(), delete: jest.fn() } };
  const storage = { putObject: jest.fn(), getObject: jest.fn(), deleteObject: jest.fn() };
  const service = new FilesService(prisma as never, storage as never);
  const upload = { originalname: 'report.cs', buffer: Buffer.from('new!'), mimetype: 'text/plain', size: 4 };

  beforeEach(() => jest.clearAllMocks());

  it('creates a new entry with uploadedBy = modifiedBy = caller', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue(null);
    prisma.fileEntry.create.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({
      ...existing, ...data, id: 'f9', storageKey: 'users/u1/f9', uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' },
    }));
    prisma.fileEntry.update.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({ ...existing, ...data, id: 'f9', uploadedBy: { username: 'bohdan' }, modifiedBy: { username: 'bohdan' } }));
    const dto = await service.upsert(owner, upload);
    expect(dto.uploadedBy).toBe('bohdan');
    expect(dto.modifiedBy).toBe('bohdan');
    expect(storage.putObject).toHaveBeenCalledWith('users/u1/f9', upload.buffer, 'text/plain');
  });

  it('overwrites an existing name: same id and key, new bytes, modifiedBy = caller', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue(existing);
    prisma.fileEntry.update.mockImplementation(async ({ data }: { data: Record<string, unknown> }) => ({
      ...existing, ...data, modifiedBy: { username: 'olena' },
    }));
    const dto = await service.upsert(editor, upload);
    expect(dto.id).toBe('f1');
    expect(dto.uploadedBy).toBe('bohdan');
    expect(dto.modifiedBy).toBe('olena');
    expect(storage.putObject).toHaveBeenCalledWith('users/u1/f1', upload.buffer, 'text/plain');
    expect(prisma.fileEntry.update.mock.calls[0][0].data).toMatchObject({ size: 4, modifiedById: 'u2' });
    expect(prisma.fileEntry.create).not.toHaveBeenCalled();
  });

  it('refuses to read a file from another space', async () => {
    prisma.fileEntry.findUnique.mockResolvedValue({ ...existing, ownerId: 'someone-else' });
    await expect(service.getContent('u1', 'f1')).rejects.toBeInstanceOf(NotFoundException);
  });
});
```

Note on the first test: `upsert` for a new file creates the row first (to get the id for the storage key), then puts the object, then updates `storageKey`; the mocks above accept that sequence.

- [ ] **Step 2: Run to verify it fails** — `yarn workspace @minidrive/api test files.service` → FAIL.

- [ ] **Step 3: Implement**

`apps/api/src/files/file.dto.ts`:
```ts
import { ApiProperty } from '@nestjs/swagger';

export class FileDto {
  @ApiProperty() id!: string;
  @ApiProperty() name!: string;
  @ApiProperty() extension!: string;
  @ApiProperty() size!: number;
  @ApiProperty() createdAt!: string;
  @ApiProperty() updatedAt!: string;
  @ApiProperty() uploadedBy!: string;
  @ApiProperty() modifiedBy!: string;
}
```

`apps/api/src/files/files.service.ts`:
```ts
import { Injectable, NotFoundException } from '@nestjs/common';
import { FileEntry } from '@prisma/client';
import { extensionOf } from '@minidrive/shared';
import { Readable } from 'stream';
import { JwtUser } from '../auth/jwt.strategy';
import { PrismaService } from '../prisma/prisma.service';
import { StorageService } from '../storage/storage.service';
import { FileDto } from './file.dto';

type Upload = { originalname: string; buffer: Buffer; mimetype: string; size: number };
type EntryWithUsers = FileEntry & { uploadedBy: { username: string }; modifiedBy: { username: string } };

const withUsers = { uploadedBy: { select: { username: true } }, modifiedBy: { select: { username: true } } };

@Injectable()
export class FilesService {
  constructor(private readonly prisma: PrismaService, private readonly storage: StorageService) {}

  async listFor(ownerId: string): Promise<FileDto[]> {
    const rows = await this.prisma.fileEntry.findMany({ where: { ownerId }, include: withUsers });
    return rows.map((r) => this.toDto(r));
  }

  async upsert(owner: JwtUser, file: Upload): Promise<FileDto> {
    const name = file.originalname;
    const found = await this.prisma.fileEntry.findUnique({
      where: { ownerId_name: { ownerId: owner.id, name } },
      include: withUsers,
    });
    if (found) {
      await this.storage.putObject(found.storageKey, file.buffer, file.mimetype);
      const updated = await this.prisma.fileEntry.update({
        where: { id: found.id },
        data: { size: file.size, updatedAt: new Date(), modifiedById: owner.id },
        include: withUsers,
      });
      return this.toDto(updated);
    }
    const created = await this.prisma.fileEntry.create({
      data: {
        ownerId: owner.id, name, extension: extensionOf(name), size: file.size, storageKey: '',
        uploadedById: owner.id, modifiedById: owner.id,
      },
      include: withUsers,
    });
    const storageKey = `users/${owner.id}/${created.id}`;
    await this.storage.putObject(storageKey, file.buffer, file.mimetype);
    const saved = await this.prisma.fileEntry.update({ where: { id: created.id }, data: { storageKey }, include: withUsers });
    return this.toDto(saved);
  }

  async getContent(ownerId: string, id: string): Promise<{ stream: Readable; mimeType: string; size?: number; name: string }> {
    const entry = await this.findOwned(ownerId, id);
    const object = await this.storage.getObject(entry.storageKey);
    return { ...object, name: entry.name };
  }

  async delete(ownerId: string, id: string): Promise<void> {
    const entry = await this.findOwned(ownerId, id);
    await this.storage.deleteObject(entry.storageKey);
    await this.prisma.fileEntry.delete({ where: { id } });
  }

  private async findOwned(ownerId: string, id: string): Promise<FileEntry> {
    const entry = await this.prisma.fileEntry.findUnique({ where: { id } });
    if (!entry || entry.ownerId !== ownerId) throw new NotFoundException('File not found');
    return entry;
  }

  private toDto(row: EntryWithUsers): FileDto {
    return {
      id: row.id,
      name: row.name,
      extension: row.extension,
      size: row.size,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
      uploadedBy: row.uploadedBy.username,
      modifiedBy: row.modifiedBy.username,
    };
  }
}
```

`apps/api/src/files/files.controller.ts`:
```ts
import {
  Controller, Delete, Get, HttpCode, Param, Post, Res, StreamableFile, UploadedFile, UseGuards, UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiBearerAuth, ApiBody, ApiConsumes, ApiTags } from '@nestjs/swagger';
import type { Response } from 'express';
import { CurrentUser } from '../auth/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { JwtUser } from '../auth/jwt.strategy';
import { loadConfig } from '../config';
import { FileDto } from './file.dto';
import { FilesService } from './files.service';

@ApiTags('files')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('files')
export class FilesController {
  constructor(private readonly files: FilesService) {}

  @Get()
  list(@CurrentUser() user: JwtUser): Promise<FileDto[]> {
    return this.files.listFor(user.id);
  }

  @Post()
  @ApiConsumes('multipart/form-data')
  @ApiBody({ schema: { type: 'object', properties: { file: { type: 'string', format: 'binary' } } } })
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: loadConfig().maxFileBytes } }))
  upload(@CurrentUser() user: JwtUser, @UploadedFile() file: Express.Multer.File): Promise<FileDto> {
    return this.files.upsert(user, file);
  }

  @Get(':id/content')
  async download(@CurrentUser() user: JwtUser, @Param('id') id: string, @Res({ passthrough: true }) res: Response): Promise<StreamableFile> {
    const content = await this.files.getContent(user.id, id);
    res.set({
      'Content-Type': content.mimeType,
      'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(content.name)}`,
    });
    if (content.size) res.set('Content-Length', String(content.size));
    return new StreamableFile(content.stream);
  }

  @Delete(':id')
  @HttpCode(204)
  remove(@CurrentUser() user: JwtUser, @Param('id') id: string): Promise<void> {
    return this.files.delete(user.id, id);
  }
}
```

Multer's `fileSize` limit makes Nest return **413 Payload Too Large** automatically.

`apps/api/src/files/files.module.ts`:
```ts
import { Module } from '@nestjs/common';
import { StorageModule } from '../storage/storage.module';
import { FilesController } from './files.controller';
import { FilesService } from './files.service';

@Module({ imports: [StorageModule], controllers: [FilesController], providers: [FilesService] })
export class FilesModule {}
```

Add `FilesModule` to `app.module.ts` imports. Ensure `apps/api/tsconfig.json` has `"esModuleInterop": true` and that `@minidrive/shared` resolves (`yarn workspace @minidrive/shared` build first; add `"prebuild": "yarn workspace @minidrive/shared"` build to the root `package.json` scripts for CI).

- [ ] **Step 4: Run tests, smoke the flow, commit**

Run: `yarn workspace @minidrive/api` test → all PASS. Then:
```bash
TOKEN=$(curl -s -X POST localhost:3000/auth/login -H 'content-type: application/json' -d '{"username":"bohdan","password":"secret123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
echo 'class Program {}' > /tmp/Program.cs
curl -s -X POST localhost:3000/files -H "Authorization: Bearer $TOKEN" -F file=@/tmp/Program.cs
curl -s localhost:3000/files -H "Authorization: Bearer $TOKEN"
```
Expected: the upload returns a `FileDto`; the list contains `Program.cs` with `uploadedBy: "bohdan"`; uploading the same name again keeps the same `id` and bumps `updatedAt`.

```bash
git add apps/api/src package.json
git commit -m "feat(api): files module with upsert, streaming download and delete"
```

---

### Task 11: API Dockerfile, seed users, smoke script

**Files:**
- Create: `docker/api.Dockerfile`, `apps/api/prisma/seed.ts`, `tools/api-smoke.sh`
- Modify: `apps/api/package.json`

**Interfaces:**
- Produces: `yarn stack:up` boots postgres, minio and the API image; `yarn workspace @minidrive/api` db:seed creates users `bohdan`, `olena`, `taras` (password `secret123`) for screenshots where «Завантажив» and «Редагував» differ.

- [ ] **Step 1: Dockerfile**

`docker/api.Dockerfile`:
```dockerfile
FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json yarn.lock .yarnrc.yml ./
COPY packages/shared/package.json packages/shared/
COPY packages/ui/package.json packages/ui/
COPY apps/api/package.json apps/api/
COPY apps/desktop/package.json apps/desktop/
RUN yarn workspaces focus @minidrive/api @minidrive/shared
COPY packages/shared packages/shared
COPY apps/api apps/api
RUN yarn workspace @minidrive/shared build && yarn workspace @minidrive/api prisma generate && yarn workspace @minidrive/api build

FROM node:22-alpine
WORKDIR /repo
ENV NODE_ENV=production
COPY --from=build /repo/node_modules node_modules
COPY --from=build /repo/packages/shared/package.json packages/shared/package.json
COPY --from=build /repo/packages/shared/dist packages/shared/dist
COPY --from=build /repo/apps/api/package.json apps/api/package.json
COPY --from=build /repo/apps/api/dist apps/api/dist
COPY --from=build /repo/apps/api/prisma apps/api/prisma
WORKDIR /repo/apps/api
EXPOSE 3000
CMD ["sh", "-c", "npx prisma migrate deploy && node dist/main"]
```
`yarn workspaces focus` installs only the listed workspaces and their dependencies; every workspace `package.json` must be copied before it so the lockfile resolves. If `apps/api/node_modules` exists after the install (unhoisted packages), add `COPY --from=build /repo/apps/api/node_modules apps/api/node_modules` to the runtime stage.

- [ ] **Step 2: Seed script**

`apps/api/prisma/seed.ts`:
```ts
import { PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcrypt';

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash('secret123', 10);
  for (const username of ['bohdan', 'olena', 'taras']) {
    await prisma.user.upsert({ where: { username }, update: {}, create: { username, passwordHash } });
  }
}

main().finally(() => prisma.$disconnect());
```

`apps/api/package.json` additions:
```json
"scripts": { "db:seed": "ts-node prisma/seed.ts" },
"prisma": { "seed": "ts-node prisma/seed.ts" }
```

- [ ] **Step 3: Smoke script**

`tools/api-smoke.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:3000}"
U="${U:-bohdan}"; P="${P:-secret123}"
TOKEN=$(curl -sf -X POST "$API/auth/login" -H 'content-type: application/json' -d "{\"username\":\"$U\",\"password\":\"$P\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
echo "login ok"
printf 'class Smoke {}\n' > /tmp/Smoke.cs
ID=$(curl -sf -X POST "$API/files" -H "Authorization: Bearer $TOKEN" -F file=@/tmp/Smoke.cs | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "upload ok ($ID)"
curl -sf "$API/files" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print("list ok:", [f["name"] for f in json.load(sys.stdin)])'
curl -sf "$API/files/$ID/content" -H "Authorization: Bearer $TOKEN" | head -c 40; echo; echo "download ok"
curl -sf -X DELETE "$API/files/$ID" -H "Authorization: Bearer $TOKEN" -o /dev/null -w "delete %{http_code}\n"
```

- [ ] **Step 4: Build the stack, seed, smoke, commit**

```bash
chmod +x tools/api-smoke.sh
yarn stack:up
yarn workspace @minidrive/api db:seed
tools/api-smoke.sh
```
Expected: `login ok`, `upload ok`, `list ok: ['Smoke.cs', ...]`, `download ok`, `delete 204`.

```bash
git add docker apps/api tools/api-smoke.sh
git commit -m "feat(api): docker image, seed users and smoke script"
```

---

## Part C — Desktop client (Electron)

### Task 12: Electron scaffold, settings store, preload bridge skeleton

**Files:**
- Create: `apps/desktop/` via electron-vite template, `apps/desktop/src/main/settings.ts`, `apps/desktop/src/preload/index.ts`, `apps/desktop/src/preload/index.d.ts`, `apps/desktop/vitest.config.ts`
- Modify: `apps/desktop/package.json`, `apps/desktop/electron.vite.config.ts`, `apps/desktop/src/main/index.ts`

**Interfaces:**
- Produces: `Settings { apiUrl: string; token: string | null; boundFolder: string | null; autoWatch: boolean }` persisted with electron-store; token encrypted with `safeStorage` (stored base64).
- Produces: the IPC channel names used by all later tasks: `settings:get`, `settings:set`, `session:setToken`, `session:getToken`, `folder:pick`, `folder:scan`, `sync:run`, `sync:watch`, `sync:status`, `file:saveAs`, `file:dragOut`. `window.minidrive` typed in `index.d.ts` (full implementation in Task 17; this task exposes only `settings` and `session`).

- [ ] **Step 1: Scaffold**

```bash
cd apps && yarn create @quick-start/electron desktop --template react-ts && cd ..
rm -rf apps/desktop/node_modules apps/desktop/yarn.lock apps/desktop/package-lock.json
```
Edit `apps/desktop/package.json`: `"name": "@minidrive/desktop"`, `"private": true`, keep template scripts (`dev`, `build`, `build:mac`, `build:win`). Then:
```bash
yarn workspace @minidrive/desktop add electron-store chokidar @minidrive/shared@workspace:*
yarn workspace @minidrive/desktop add -D vitest
yarn install
```

- [ ] **Step 2: Vitest for main-process units**

`apps/desktop/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
```
Add `"test": "vitest run"` to the desktop scripts.

- [ ] **Step 3: Settings store**

`apps/desktop/src/main/settings.ts`:
```ts
import Store from 'electron-store';
import { safeStorage } from 'electron';

export type Settings = { apiUrl: string; token: string | null; boundFolder: string | null; autoWatch: boolean };

const store = new Store<{ apiUrl: string; tokenEncrypted: string | null; boundFolder: string | null; autoWatch: boolean }>({
  defaults: { apiUrl: 'http://localhost:3000', tokenEncrypted: null, boundFolder: null, autoWatch: false },
});

export function getSettings(): Settings {
  return {
    apiUrl: store.get('apiUrl'),
    token: decrypt(store.get('tokenEncrypted')),
    boundFolder: store.get('boundFolder'),
    autoWatch: store.get('autoWatch'),
  };
}

export function updateSettings(patch: Partial<Omit<Settings, 'token'>>): Settings {
  if (patch.apiUrl !== undefined) store.set('apiUrl', patch.apiUrl.replace(/\/+$/, ''));
  if (patch.boundFolder !== undefined) store.set('boundFolder', patch.boundFolder);
  if (patch.autoWatch !== undefined) store.set('autoWatch', patch.autoWatch);
  return getSettings();
}

export function setToken(token: string | null): void {
  if (!token) {
    store.set('tokenEncrypted', null);
    return;
  }
  const value = safeStorage.isEncryptionAvailable()
    ? safeStorage.encryptString(token).toString('base64')
    : Buffer.from(token, 'utf8').toString('base64');
  store.set('tokenEncrypted', value);
}

function decrypt(value: string | null): string | null {
  if (!value) return null;
  const buffer = Buffer.from(value, 'base64');
  return safeStorage.isEncryptionAvailable() ? safeStorage.decryptString(buffer) : buffer.toString('utf8');
}
```

- [ ] **Step 4: Main process window + first IPC handlers**

Replace `apps/desktop/src/main/index.ts` body with:
```ts
import { app, BrowserWindow, ipcMain, shell } from 'electron';
import { join } from 'path';
import { electronApp, is, optimizer } from '@electron-toolkit/utils';
import { getSettings, setToken, updateSettings } from './settings';

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), sandbox: false },
  });
  win.on('ready-to-show', () => win.show());
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  if (is.dev && process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'));
  }
  return win;
}

function registerIpc(): void {
  ipcMain.handle('settings:get', () => getSettings());
  ipcMain.handle('settings:set', (_e, patch) => updateSettings(patch));
  ipcMain.handle('session:setToken', (_e, token: string | null) => setToken(token));
  ipcMain.handle('session:getToken', () => getSettings().token);
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('ua.knu.minidrive');
  app.on('browser-window-created', (_, window) => optimizer.watchWindowShortcuts(window));
  registerIpc();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
```

- [ ] **Step 5: Preload bridge**

`apps/desktop/src/preload/index.ts`:
```ts
import { contextBridge, ipcRenderer } from 'electron';

const minidrive = {
  settings: {
    get: () => ipcRenderer.invoke('settings:get'),
    set: (patch: Record<string, unknown>) => ipcRenderer.invoke('settings:set', patch),
  },
  session: {
    setToken: (token: string | null) => ipcRenderer.invoke('session:setToken', token),
    getToken: () => ipcRenderer.invoke('session:getToken'),
  },
};

contextBridge.exposeInMainWorld('minidrive', minidrive);

export type MinidriveApi = typeof minidrive;
```

`apps/desktop/src/preload/index.d.ts`:
```ts
import type { MinidriveApi } from './index';

declare global {
  interface Window {
    minidrive: MinidriveApi;
  }
}
```

- [ ] **Step 6: Run and commit**

Run: `yarn workspace @minidrive/desktop` dev
Expected: the template window opens; in DevTools `await window.minidrive.settings.get()` returns `{ apiUrl: 'http://localhost:3000', token: null, boundFolder: null, autoWatch: false }`.

```bash
git add apps/desktop yarn.lock
git commit -m "feat(desktop): electron scaffold, settings store and preload bridge"
```

---

### Task 13: Renderer — session, ApiClient wiring, login screen

**Files:**
- Create: `apps/desktop/src/renderer/src/api.ts`, `apps/desktop/src/renderer/src/session.ts`, `apps/desktop/src/renderer/src/screens/LoginScreen.tsx`, `apps/desktop/src/renderer/src/App.tsx` (replace template), `apps/desktop/src/renderer/src/styles.css` (replace template css)
- Remove: template `assets/`, `components/Versions.tsx`

**Interfaces:**
- Produces: `getApi(): ApiClient` (singleton bound to `settings.apiUrl` + token), `SessionStore { load(): Promise<{ token: string | null; apiUrl: string }>; save(token, apiUrl); clear() }`, `LoginScreen` props `{ onLoggedIn: (user: UserDto) => void }`; `App` switches between `LoginScreen` and `DriveScreen` (Task 14).

- [ ] **Step 1: api.ts and session.ts**

`apps/desktop/src/renderer/src/api.ts`:
```ts
import { ApiClient } from '@minidrive/shared';

let client = new ApiClient('http://localhost:3000');

export function configureApi(baseUrl: string, token: string | null): ApiClient {
  client = new ApiClient(baseUrl, token);
  return client;
}

export function getApi(): ApiClient {
  return client;
}
```

`apps/desktop/src/renderer/src/session.ts`:
```ts
import { configureApi } from './api';

export const SessionStore = {
  async load() {
    const settings = await window.minidrive.settings.get();
    configureApi(settings.apiUrl, settings.token);
    return { token: settings.token as string | null, apiUrl: settings.apiUrl as string };
  },
  async save(token: string, apiUrl: string) {
    await window.minidrive.settings.set({ apiUrl });
    await window.minidrive.session.setToken(token);
    configureApi(apiUrl, token);
  },
  async clear() {
    await window.minidrive.session.setToken(null);
    const settings = await window.minidrive.settings.get();
    configureApi(settings.apiUrl, null);
  },
};
```

- [ ] **Step 2: LoginScreen**

`apps/desktop/src/renderer/src/screens/LoginScreen.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { ApiError, type UserDto } from '@minidrive/shared';
import { configureApi, getApi } from '../api';
import { SessionStore } from '../session';

type Props = { onLoggedIn: (user: UserDto) => void };

export function LoginScreen({ onLoggedIn }: Props) {
  const [apiUrl, setApiUrl] = useState('http://localhost:3000');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    SessionStore.load().then((s) => setApiUrl(s.apiUrl));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const api = configureApi(apiUrl.trim().replace(/\/+$/, ''), null);
      const res = mode === 'login' ? await api.login(username, password) : await api.register(username, password);
      await SessionStore.save(res.accessToken, api.baseUrl);
      onLoggedIn(res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Сервер недоступний');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <h1>MiniDrive</h1>
        <label>
          Адреса сервера
          <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://localhost:3000" />
        </label>
        <label>
          Ім'я користувача
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {mode === 'login' ? 'Увійти' : 'Зареєструватися'}
        </button>
        <button type="button" className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Уже є обліковий запис? Увійти'}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: App.tsx**

```tsx
import { useEffect, useState } from 'react';
import type { UserDto } from '@minidrive/shared';
import { getApi } from './api';
import { LoginScreen } from './screens/LoginScreen';
import { DriveScreen } from './screens/DriveScreen';
import { SessionStore } from './session';

export default function App() {
  const [user, setUser] = useState<UserDto | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    SessionStore.load()
      .then(async (s) => {
        if (s.token) setUser(await getApi().me());
      })
      .catch(() => SessionStore.clear())
      .finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return <LoginScreen onLoggedIn={setUser} />;
  return (
    <DriveScreen
      user={user}
      onLogout={async () => {
        await SessionStore.clear();
        setUser(null);
      }}
    />
  );
}
```

Create a placeholder `screens/DriveScreen.tsx` exporting `DriveScreen({ user, onLogout })` that renders the username and a «Вийти» button, so the app compiles; Task 14 replaces it.

- [ ] **Step 4: Styles**

Replace the template CSS with `styles.css` (imported from `main.tsx`); it already contains the classes used by Tasks 14, 15 and 18:

```css
:root { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 14px; color: #1c2230; background: #f4f5f8; }
* { box-sizing: border-box; }
body { margin: 0; }
button { padding: 6px 12px; border: 1px solid #c7ccd6; border-radius: 6px; background: #fff; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
button.link { border: none; background: none; color: #3d5a99; }
input, select { padding: 6px 8px; border: 1px solid #c7ccd6; border-radius: 6px; font: inherit; }
.error { color: #b3261e; margin: 4px 0; }

.login { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card { width: 360px; display: grid; gap: 12px; padding: 24px; background: #fff; border: 1px solid #d9dde6; border-radius: 8px; }
.login-card label { display: grid; gap: 4px; }
.login-card input { width: 100%; }

.drive { height: 100vh; display: grid; grid-template-rows: auto auto auto 1fr; grid-template-columns: 2fr 1fr; gap: 12px; padding: 12px; }
.drive > header { grid-column: 1 / -1; display: flex; gap: 16px; align-items: center; }
.drive > header span { margin-left: auto; }
.toolbar { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.columns { display: flex; flex-wrap: wrap; gap: 8px 12px; }
.sync { grid-column: 1 / -1; display: grid; gap: 6px; padding: 10px 12px; background: #fff; border: 1px solid #d9dde6; border-radius: 8px; }
.sync .folder, .sync .actions { display: flex; gap: 12px; align-items: center; }
.sync .folder span { font-family: Menlo, monospace; font-size: 12px; overflow: hidden; text-overflow: ellipsis; }

.dropzone { position: relative; min-height: 200px; overflow: auto; background: #fff; border: 1px solid #d9dde6; border-radius: 8px; }
.dropzone.over { outline: 2px dashed #3d5a99; }
.drop-hint { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(61, 90, 153, .08); font-weight: 600; pointer-events: none; }
table.files { width: 100%; border-collapse: collapse; }
table.files th, table.files td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #eceff4; white-space: nowrap; }
table.files tbody tr { cursor: pointer; }
table.files tbody tr:nth-child(even) { background: #fafbfd; }
table.files tbody tr.selected { background: #dae8fc; }
table.files td.empty { color: #7b8497; text-align: center; padding: 24px; }

.preview { overflow: auto; padding: 12px; background: #fff; border: 1px solid #d9dde6; border-radius: 8px; }
.preview.empty { color: #7b8497; }
.preview dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 0 0 12px; }
.preview dt { color: #7b8497; } .preview dd { margin: 0; }
.preview pre { font: 12px/1.5 Menlo, monospace; white-space: pre-wrap; word-break: break-word; }
.preview img { max-width: 100%; height: auto; }
```

- [ ] **Step 5: Run, verify login, commit**

Run: `yarn workspace @minidrive/desktop` dev with the API running.
Expected: login with `bohdan` / `secret123` shows the placeholder drive screen with the username; restarting the app skips the login (token restored); «Вийти» returns to the login screen.

```bash
git add apps/desktop/src
git commit -m "feat(desktop): login screen and session handling"
```

---

### Task 14: Shared DriveViewModel, `packages/ui` components, DriveScreen

**Files:**
- Create: `packages/shared/src/driveViewModel.ts`, `packages/ui/package.json`, `packages/ui/tsconfig.json`, `packages/ui/src/index.ts`, `packages/ui/src/useDrive.ts`, `packages/ui/src/FileTable.tsx`, `packages/ui/src/SortControl.tsx`, `packages/ui/src/FilterControl.tsx`, `packages/ui/src/ColumnToggle.tsx`, `packages/ui/src/styles.css`, `apps/desktop/src/renderer/src/screens/DriveScreen.tsx` (replace placeholder)
- Modify: `packages/shared/src/index.ts` (add `export * from './driveViewModel';`), `apps/desktop/electron.vite.config.ts` (renderer `resolve.alias` not needed; `@minidrive/ui` ships TSX source, so add `optimizeDeps.include: ['@minidrive/ui']` is unnecessary — Vite compiles workspace TSX directly)
- Test: `packages/shared/src/driveViewModel.test.ts`

**Interfaces:**
- Produces (shared): `class DriveViewModel { files: FileDto[]; order: SortOrder; filter: FileFilter; columns: ColumnVisibility; selected: FileDto | null; setFiles(f); setOrder(o); setFilter(f); toggleColumn(k); select(f); get visibleFiles(): FileDto[] }` (pure, no React).
- Produces (ui): `useDrive(api: ApiClient, onUnauthorized: () => void)` returning `{ vm, refresh(), update(fn), busy, error, setError }`; `packages/ui` package `@minidrive/ui` with `"main": "src/index.ts"` (TSX source consumed by Vite and Next.js `transpilePackages`), peer dependency `react`.
- `FileTable` props: `{ files: FileDto[]; columns: ColumnVisibility; selected: FileDto | null; onSelect(f); onDragStart?(f) }`. `SortControl` props `{ order; onChange }`. `FilterControl` props `{ filter; onChange }`. `ColumnToggle` props `{ columns; onToggle(key) }`.

- [ ] **Step 1: Write the failing test (variant operations through the view model)**

`packages/shared/src/driveViewModel.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import type { FileDto } from './types';
import { DriveViewModel } from './driveViewModel';

const f = (name: string): FileDto => ({
  id: name, name, extension: '', size: 1, createdAt: '', updatedAt: '', uploadedBy: 'b', modifiedBy: 'b',
});

describe('DriveViewModel', () => {
  it('applies sort by name and the cpp/png filter to visibleFiles', () => {
    const vm = new DriveViewModel();
    vm.setFiles([f('z.png'), f('a.cs'), f('m.cpp'), f('B.txt')]);
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['a.cs', 'B.txt', 'm.cpp', 'z.png']);
    vm.setOrder('desc');
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['z.png', 'm.cpp', 'B.txt', 'a.cs']);
    vm.setFilter('cpp-png');
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['z.png', 'm.cpp']);
  });

  it('cannot hide the name column', () => {
    const vm = new DriveViewModel();
    vm.toggleColumn('name');
    vm.toggleColumn('size');
    expect(vm.columns.name).toBe(true);
    expect(vm.columns.size).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `yarn workspace @minidrive/shared` test → FAIL.

- [ ] **Step 3: Implement `packages/shared/src/driveViewModel.ts` and create `packages/ui`**

```ts
import { DEFAULT_COLUMNS, toggleColumn } from './columns';
import { filterByType, sortByName } from './fileList';
import type { ColumnKey, ColumnVisibility, FileDto, FileFilter, SortOrder } from './types';

export class DriveViewModel {
  files: FileDto[] = [];
  order: SortOrder = 'asc';
  filter: FileFilter = 'all';
  columns: ColumnVisibility = DEFAULT_COLUMNS;
  selected: FileDto | null = null;

  setFiles(files: FileDto[]): void {
    this.files = files;
    if (this.selected && !files.some((f) => f.id === this.selected!.id)) this.selected = null;
  }

  setOrder(order: SortOrder): void {
    this.order = order;
  }

  setFilter(filter: FileFilter): void {
    this.filter = filter;
  }

  toggleColumn(key: ColumnKey): void {
    this.columns = toggleColumn(this.columns, key);
  }

  select(file: FileDto | null): void {
    this.selected = file;
  }

  get visibleFiles(): FileDto[] {
    return filterByType(sortByName(this.files, this.order), this.filter);
  }
}
```

`packages/ui/package.json`:
```json
{
  "name": "@minidrive/ui",
  "version": "0.1.0",
  "private": true,
  "main": "src/index.ts",
  "types": "src/index.ts",
  "peerDependencies": { "react": ">=18" },
  "dependencies": { "@minidrive/shared": "workspace:*" },
  "devDependencies": { "@types/react": "^19.0.0", "typescript": "^5.6.0" }
}
```
`packages/ui/tsconfig.json`: extends the base config with `"jsx": "react-jsx"`, `"lib": ["ES2022", "DOM"]`, `"noEmit": true`, `"include": ["src"]`. `packages/ui/src/index.ts` re-exports every component and `useDrive`. Run `yarn workspace @minidrive/desktop add @minidrive/ui@workspace:*` after creating the package.

- [ ] **Step 4: useDrive hook (`packages/ui/src/useDrive.ts`)**

```ts
import { useCallback, useMemo, useReducer, useState } from 'react';
import { ApiClient, ApiError, DriveViewModel } from '@minidrive/shared';

export function useDrive(api: ApiClient, onUnauthorized: () => void) {
  const vm = useMemo(() => new DriveViewModel(), []);
  const [, rerender] = useReducer((n: number) => n + 1, 0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      vm.setFiles(await api.listFiles());
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) onUnauthorized();
      else setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
      rerender();
    }
  }, [vm, api, onUnauthorized]);

  const update = useCallback((fn: (vm: DriveViewModel) => void) => {
    fn(vm);
    rerender();
  }, [vm]);

  return { vm, refresh, update, busy, error, setError };
}
```

- [ ] **Step 5: Components in `packages/ui/src/`**

`FileTable.tsx`:
```tsx
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
```

`SortControl.tsx`:
```tsx
import type { SortOrder } from '@minidrive/shared';

export function SortControl({ order, onChange }: { order: SortOrder; onChange: (o: SortOrder) => void }) {
  return (
    <button type="button" onClick={() => onChange(order === 'asc' ? 'desc' : 'asc')} title="Сортування за назвою">
      Назва {order === 'asc' ? '↑' : '↓'}
    </button>
  );
}
```

`FilterControl.tsx`:
```tsx
import type { FileFilter } from '@minidrive/shared';

export function FilterControl({ filter, onChange }: { filter: FileFilter; onChange: (f: FileFilter) => void }) {
  return (
    <select value={filter} onChange={(e) => onChange(e.target.value as FileFilter)} title="Фільтр за типом">
      <option value="all">Усі файли</option>
      <option value="cpp-png">Лише .cpp, .png</option>
    </select>
  );
}
```

`ColumnToggle.tsx`:
```tsx
import { COLUMN_KEYS, COLUMN_LABELS, type ColumnKey, type ColumnVisibility } from '@minidrive/shared';

export function ColumnToggle({ columns, onToggle }: { columns: ColumnVisibility; onToggle: (k: ColumnKey) => void }) {
  return (
    <div className="columns">
      {COLUMN_KEYS.filter((k) => k !== 'name').map((k) => (
        <label key={k}>
          <input type="checkbox" checked={columns[k]} onChange={() => onToggle(k)} /> {COLUMN_LABELS[k]}
        </label>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: DriveScreen (list, sort, filter, columns; actions come in Task 15)**

```tsx
import { useEffect } from 'react';
import type { UserDto } from '@minidrive/shared';
import { ColumnToggle, FileTable, FilterControl, SortControl, useDrive } from '@minidrive/ui';
import { getApi } from '../api';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const { vm, refresh, update, busy, error } = useDrive(getApi(), onLogout);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="drive">
      <header>
        <strong>MiniDrive</strong>
        <span>{user.username}</span>
        <button type="button" onClick={onLogout}>Вийти</button>
      </header>
      <div className="toolbar">
        <SortControl order={vm.order} onChange={(o) => update((m) => m.setOrder(o))} />
        <FilterControl filter={vm.filter} onChange={(f) => update((m) => m.setFilter(f))} />
        <ColumnToggle columns={vm.columns} onToggle={(k) => update((m) => m.toggleColumn(k))} />
        <button type="button" onClick={refresh} disabled={busy}>Оновити</button>
      </div>
      {error && <p className="error">{error}</p>}
      <FileTable files={vm.visibleFiles} columns={vm.columns} selected={vm.selected} onSelect={(f) => update((m) => m.select(f))} />
    </div>
  );
}
```

Move the component classes (`.toolbar`, `.columns`, `.dropzone`, `.drop-hint`, `table.files`, `.preview`) from the desktop `styles.css` into `packages/ui/src/styles.css` and import it from the desktop `main.tsx` (`import '@minidrive/ui/src/styles.css'`); the desktop file keeps only `:root`, `.login*`, `.drive`, `.sync` rules.

- [ ] **Step 7: Run tests and the app, commit**

Run: `yarn workspace @minidrive/shared` test → PASS. Run the app: uploading a few files via `tools/api-smoke.sh`-style curl shows them; the sort button flips order; the filter hides everything except `.cpp`/`.png`; unchecking columns hides them and «Назва» stays.

```bash
git add packages apps/desktop yarn.lock
git commit -m "feat(ui): shared react components and drive view model"
```

---

### Task 15: Preview, upload (button + drag-and-drop), download, delete

**Files:**
- Create: `packages/ui/src/PreviewPanel.tsx`, `packages/ui/src/UploadDropzone.tsx` (export both from `packages/ui/src/index.ts`)
- Modify: `apps/desktop/src/renderer/src/screens/DriveScreen.tsx`, `apps/desktop/src/main/index.ts`, `apps/desktop/src/preload/index.ts`

**Interfaces:**
- Consumes: `createPreview(entry)`, `getApi().download/upload/remove`.
- Produces: IPC `file:saveAs(name: string, bytes: ArrayBuffer): Promise<string | null>` (save dialog + write; returns the path or null when cancelled). `PreviewPanel` props `{ file: FileDto | null; loadContent: (file: FileDto) => Promise<Blob> }` — the caller passes `(f) => getApi().download(f.id)` on desktop and the web client passes its own loader. `UploadDropzone` props `{ onFiles: (files: File[]) => void; busy: boolean }` — renders the «Завантажити файли» button (hidden `<input type=file multiple>`) and accepts dropped files anywhere inside it.

- [ ] **Step 1: IPC for save-as (main + preload)**

In `main/index.ts` `registerIpc()` add:
```ts
ipcMain.handle('file:saveAs', async (e, name: string, bytes: ArrayBuffer) => {
  const win = BrowserWindow.fromWebContents(e.sender);
  const { canceled, filePath } = await dialog.showSaveDialog(win!, { defaultPath: name });
  if (canceled || !filePath) return null;
  await fs.writeFile(filePath, Buffer.from(bytes));
  return filePath;
});
```
with `import { dialog } from 'electron'` and `import { promises as fs } from 'fs'`. In preload add `file: { saveAs: (name: string, bytes: ArrayBuffer) => ipcRenderer.invoke('file:saveAs', name, bytes) }`.

- [ ] **Step 2: PreviewPanel**

```tsx
import { useEffect, useState } from 'react';
import { createPreview, type FileDto, type PreviewResult } from '@minidrive/shared';

type Props = { file: FileDto | null; loadContent: (file: FileDto) => Promise<Blob> };

export function PreviewPanel({ file, loadContent }: Props) {
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'unsupported' | 'error'>('idle');

  useEffect(() => {
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
        if (r.kind === 'image') url = r.url;
        setResult(r);
        setState('idle');
      })
      .catch(() => setState('error'));
    return () => {
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
```

- [ ] **Step 3: UploadDropzone**

```tsx
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
```

- [ ] **Step 4: Wire actions into DriveScreen**

Add to `DriveScreen`:
```tsx
const [working, setWorking] = useState(false);

async function uploadFiles(files: File[]) {
  setWorking(true);
  try {
    for (const f of files) await getApi().upload(f.name, f, f.type || 'application/octet-stream');
    await refresh();
  } catch (err) {
    setError(err instanceof Error ? err.message : String(err));
  } finally {
    setWorking(false);
  }
}

async function downloadSelected() {
  if (!vm.selected) return;
  const blob = await getApi().download(vm.selected.id);
  await window.minidrive.file.saveAs(vm.selected.name, await blob.arrayBuffer());
}

async function deleteSelected() {
  if (!vm.selected || !confirm(`Видалити «${vm.selected.name}»?`)) return;
  await getApi().remove(vm.selected.id);
  await refresh();
}
```
Toolbar gains «Вивантажити» and «Видалити» buttons (disabled without a selection). Wrap the table in `<UploadDropzone onFiles={uploadFiles} busy={working}>`, and render `<PreviewPanel file={vm.selected} loadContent={(f) => getApi().download(f.id)} />` in a right-hand column (`.drive` becomes a two-column grid: table 2fr, preview 1fr).

- [ ] **Step 5: Run and verify, commit**

Checklist in the running app:
- click `Program.cs` → source shown in `<pre>`; click a `.jpg` → image shown; click a `.zip` → «недоступний».
- «Завантажити файли» and dropping files onto the table both upload; re-uploading `Program.cs` keeps one row and updates «Змінено».
- «Вивантажити» opens the save dialog and writes the file; «Видалити» removes it.

```bash
git add packages/ui apps/desktop/src
git commit -m "feat(ui,desktop): preview, upload with drag-and-drop, download and delete"
```

---

### Task 16: Main process — LocalFolderScanner and SyncEngine (tested)

**Files:**
- Create: `apps/desktop/src/main/sync/localFolderScanner.ts`, `apps/desktop/src/main/sync/syncEngine.ts`
- Test: `apps/desktop/src/main/sync/syncEngine.test.ts`

**Interfaces:**
- Produces: `LocalFolderScanner.scan(dir: string): Promise<LocalFileInfo[]>` (top-level regular files only, skips dotfiles).
- Produces: `class SyncEngine { constructor(api: SyncApi, scanner = LocalFolderScanner); scan(dir): Promise<LocalFileInfo[]>; synchronize(dir: string, onProgress?: (done: number, total: number) => void): Promise<SyncReport> }` where `type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>`. After a download the file's mtime is set to the remote `updatedAt`.

- [ ] **Step 1: Write the failing test**

`syncEngine.test.ts`:
```ts
import { mkdtemp, readFile, stat, utimes, writeFile } from 'fs/promises';
import { tmpdir } from 'os';
import { join } from 'path';
import { describe, expect, it } from 'vitest';
import type { FileDto } from '@minidrive/shared';
import { SyncEngine } from './syncEngine';

const remoteFile = (name: string, body: string, updatedAt: string): FileDto & { body: string } => ({
  id: `r-${name}`, name, extension: '', size: Buffer.byteLength(body), createdAt: updatedAt, updatedAt, uploadedBy: 'olena', modifiedBy: 'olena', body,
});

function fakeApi(remote: (FileDto & { body: string })[]) {
  const uploads: string[] = [];
  return {
    uploads,
    listFiles: async () => remote.map(({ body, ...dto }) => dto),
    upload: async (name: string) => {
      uploads.push(name);
      return remote[0] ?? remoteFile(name, '', new Date().toISOString());
    },
    download: async (id: string) => new Blob([remote.find((r) => r.id === id)!.body]),
  };
}

describe('SyncEngine', () => {
  it('uploads local-only files, downloads remote-only files and sets mtime', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'local.txt'), 'hello');
    const remoteUpdated = '2026-09-01T10:00:00.000Z';
    const api = fakeApi([remoteFile('remote.cs', 'class R {}', remoteUpdated)]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(api.uploads).toEqual(['local.txt']);
    expect(await readFile(join(dir, 'remote.cs'), 'utf8')).toBe('class R {}');
    expect(Math.abs((await stat(join(dir, 'remote.cs'))).mtimeMs - Date.parse(remoteUpdated))).toBeLessThan(1000);
    expect(report).toMatchObject({ uploaded: 1, downloaded: 1, skipped: 0, failed: 0 });
  });

  it('skips a file that is identical on both sides', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    const updatedAt = '2026-09-01T10:00:00.000Z';
    await writeFile(join(dir, 'same.cpp'), 'int main(){}');
    await utimes(join(dir, 'same.cpp'), new Date(updatedAt), new Date(updatedAt));
    const api = fakeApi([remoteFile('same.cpp', 'int main(){}', updatedAt)]);
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report).toMatchObject({ uploaded: 0, downloaded: 0, skipped: 1 });
  });

  it('counts failures instead of aborting', async () => {
    const dir = await mkdtemp(join(tmpdir(), 'minidrive-'));
    await writeFile(join(dir, 'a.txt'), 'a');
    const api = fakeApi([]);
    api.upload = async () => { throw new Error('network'); };
    const report = await new SyncEngine(api).synchronize(dir);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('a.txt');
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `yarn workspace @minidrive/desktop` test → FAIL.

- [ ] **Step 3: Implement scanner and engine**

`localFolderScanner.ts`:
```ts
import { readdir, stat } from 'fs/promises';
import { join } from 'path';
import type { LocalFileInfo } from '@minidrive/shared';

export const LocalFolderScanner = {
  async scan(dir: string): Promise<LocalFileInfo[]> {
    const entries = await readdir(dir, { withFileTypes: true });
    const files: LocalFileInfo[] = [];
    for (const entry of entries) {
      if (!entry.isFile() || entry.name.startsWith('.')) continue;
      const s = await stat(join(dir, entry.name));
      files.push({ name: entry.name, size: s.size, mtime: s.mtimeMs });
    }
    return files;
  },
};
```

`syncEngine.ts`:
```ts
import { readFile, utimes, writeFile } from 'fs/promises';
import { join } from 'path';
import { computeSyncPlan, type ApiClient, type FileDto, type LocalFileInfo, type SyncReport } from '@minidrive/shared';
import { LocalFolderScanner } from './localFolderScanner';

export type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>;
type Progress = (done: number, total: number) => void;

export class SyncEngine {
  constructor(private readonly api: SyncApi, private readonly scanner = LocalFolderScanner) {}

  scan(dir: string): Promise<LocalFileInfo[]> {
    return this.scanner.scan(dir);
  }

  async synchronize(dir: string, onProgress?: Progress): Promise<SyncReport> {
    const [local, remote] = await Promise.all([this.scan(dir), this.api.listFiles()]);
    const plan = computeSyncPlan(local, remote);
    const remoteByName = new Map(remote.map((r) => [r.name, r]));
    const report: SyncReport = { uploaded: 0, downloaded: 0, skipped: plan.skipped.length, failed: 0, errors: [] };
    const total = plan.uploads.length + plan.downloads.length;
    let done = 0;

    for (const action of plan.uploads) {
      try {
        await this.api.upload(action.name, await readFile(join(dir, action.name)));
        report.uploaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    for (const action of plan.downloads) {
      try {
        await this.downloadTo(dir, remoteByName.get(action.name)!);
        report.downloaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }
    return report;
  }

  private async downloadTo(dir: string, file: FileDto): Promise<void> {
    const blob = await this.api.download(file.id);
    const target = join(dir, file.name);
    await writeFile(target, Buffer.from(await blob.arrayBuffer()));
    const t = new Date(file.updatedAt);
    await utimes(target, t, t);
  }
}
```

- [ ] **Step 4: Run tests and commit**

Run: `yarn workspace @minidrive/desktop` test → PASS (5 tests total with Task 14).

```bash
git add apps/desktop/src/main/sync
git commit -m "feat(desktop): folder scanner and sync engine"
```

---

### Task 17: Main process — folder binding, sync IPC, FolderWatcher, DragOutHandler

**Files:**
- Create: `apps/desktop/src/main/sync/folderWatcher.ts`, `apps/desktop/src/main/dragOutHandler.ts`, `apps/desktop/src/main/ipc.ts`
- Modify: `apps/desktop/src/main/index.ts` (replace `registerIpc` with `registerIpc(win)` from `ipc.ts`), `apps/desktop/src/preload/index.ts`
- Create: `apps/desktop/resources/drag.png` (any 64×64 icon; the template's `icon.png` resized is fine)

**Interfaces:**
- Produces IPC (all in preload under `window.minidrive`):
  - `folder.pick(): Promise<string | null>` — directory dialog, saves `boundFolder`.
  - `sync.run(): Promise<SyncReport>` — uses `boundFolder`; throws `'Папку не прив'язано'` if none. Emits `sync:progress` events `{ done, total }` to the renderer.
  - `sync.watch(enabled: boolean): Promise<boolean>` — starts/stops `FolderWatcher`; persists `autoWatch`.
  - `sync.onProgress(cb)`, `sync.onAutoSync(cb: (report: SyncReport) => void)` — subscriptions.
  - `file.dragOut(file: FileDto): void` — `DragOutHandler`: downloads to `app.getPath('temp')/minidrive/<id>/<name>` (cached) and calls `webContents.startDrag`.
- `FolderWatcher { start(dir, onChange: () => void): void; stop(): void }` using chokidar with `ignoreInitial: true`, `depth: 0`, and a 2000 ms debounce; ignores events while a sync is running.
- The main process builds its own `ApiClient` from settings (`apiUrl`, token) on every call.

- [ ] **Step 1: FolderWatcher**

```ts
import chokidar, { type FSWatcher } from 'chokidar';

const DEBOUNCE_MS = 2000;

export class FolderWatcher {
  private watcher: FSWatcher | null = null;
  private timer: NodeJS.Timeout | null = null;

  start(dir: string, onChange: () => void): void {
    this.stop();
    this.watcher = chokidar.watch(dir, { ignoreInitial: true, depth: 0, ignored: /(^|[\/\\])\../ });
    this.watcher.on('all', () => {
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(onChange, DEBOUNCE_MS);
    });
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.watcher?.close();
    this.watcher = null;
  }

  get active(): boolean {
    return this.watcher !== null;
  }
}
```

- [ ] **Step 2: DragOutHandler**

```ts
import { app, type WebContents } from 'electron';
import { mkdir, writeFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import type { ApiClient, FileDto } from '@minidrive/shared';

export class DragOutHandler {
  constructor(private readonly iconPath: string) {}

  async startDrag(sender: WebContents, api: ApiClient, file: FileDto): Promise<void> {
    const dir = join(app.getPath('temp'), 'minidrive', file.id);
    const target = join(dir, file.name);
    if (!existsSync(target)) {
      await mkdir(dir, { recursive: true });
      const blob = await api.download(file.id);
      await writeFile(target, Buffer.from(await blob.arrayBuffer()));
    }
    sender.startDrag({ file: target, icon: this.iconPath });
  }
}
```

- [ ] **Step 3: ipc.ts**

```ts
import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { promises as fs } from 'fs';
import { join } from 'path';
import { ApiClient, type FileDto } from '@minidrive/shared';
import { DragOutHandler } from './dragOutHandler';
import { getSettings, setToken, updateSettings } from './settings';
import { FolderWatcher } from './sync/folderWatcher';
import { SyncEngine } from './sync/syncEngine';

const watcher = new FolderWatcher();
const dragOut = new DragOutHandler(join(__dirname, '../../resources/drag.png'));
let syncing = false;

function api(): ApiClient {
  const s = getSettings();
  return new ApiClient(s.apiUrl, s.token);
}

async function runSync(win: BrowserWindow) {
  const { boundFolder } = getSettings();
  if (!boundFolder) throw new Error("Папку не прив'язано");
  if (syncing) throw new Error('Синхронізація вже виконується');
  syncing = true;
  try {
    return await new SyncEngine(api()).synchronize(boundFolder, (done, total) => win.webContents.send('sync:progress', { done, total }));
  } finally {
    syncing = false;
  }
}

function setWatch(win: BrowserWindow, enabled: boolean): boolean {
  const { boundFolder } = getSettings();
  updateSettings({ autoWatch: enabled });
  if (!enabled || !boundFolder) {
    watcher.stop();
    return false;
  }
  watcher.start(boundFolder, async () => {
    if (syncing) return;
    try {
      win.webContents.send('sync:auto', await runSync(win));
    } catch (err) {
      win.webContents.send('sync:auto', { uploaded: 0, downloaded: 0, skipped: 0, failed: 1, errors: [(err as Error).message] });
    }
  });
  return true;
}

export function registerIpc(win: BrowserWindow): void {
  ipcMain.handle('settings:get', () => getSettings());
  ipcMain.handle('settings:set', (_e, patch) => updateSettings(patch));
  ipcMain.handle('session:setToken', (_e, token: string | null) => setToken(token));
  ipcMain.handle('session:getToken', () => getSettings().token);

  ipcMain.handle('file:saveAs', async (_e, name: string, bytes: ArrayBuffer) => {
    const { canceled, filePath } = await dialog.showSaveDialog(win, { defaultPath: name });
    if (canceled || !filePath) return null;
    await fs.writeFile(filePath, Buffer.from(bytes));
    return filePath;
  });
  ipcMain.on('file:dragOut', (e, file: FileDto) => {
    dragOut.startDrag(e.sender, api(), file).catch(() => undefined);
  });

  ipcMain.handle('folder:pick', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
    if (canceled || filePaths.length === 0) return null;
    updateSettings({ boundFolder: filePaths[0] });
    if (getSettings().autoWatch) setWatch(win, true);
    return filePaths[0];
  });
  ipcMain.handle('sync:run', () => runSync(win));
  ipcMain.handle('sync:watch', (_e, enabled: boolean) => setWatch(win, enabled));
  ipcMain.handle('sync:status', () => ({ syncing, watching: watcher.active, boundFolder: getSettings().boundFolder, autoWatch: getSettings().autoWatch }));

  if (getSettings().autoWatch) setWatch(win, true);
  app.on('before-quit', () => watcher.stop());
}
```

In `main/index.ts`, replace the local `registerIpc()` with `registerIpc(win)` called right after `createWindow()` returns the window.

- [ ] **Step 4: Preload additions**

```ts
folder: { pick: () => ipcRenderer.invoke('folder:pick') },
sync: {
  run: () => ipcRenderer.invoke('sync:run'),
  watch: (enabled: boolean) => ipcRenderer.invoke('sync:watch', enabled),
  status: () => ipcRenderer.invoke('sync:status'),
  onProgress: (cb: (p: { done: number; total: number }) => void) => {
    const listener = (_: unknown, p: { done: number; total: number }) => cb(p);
    ipcRenderer.on('sync:progress', listener);
    return () => ipcRenderer.removeListener('sync:progress', listener);
  },
  onAutoSync: (cb: (report: unknown) => void) => {
    const listener = (_: unknown, r: unknown) => cb(r);
    ipcRenderer.on('sync:auto', listener);
    return () => ipcRenderer.removeListener('sync:auto', listener);
  },
},
file: {
  saveAs: (name: string, bytes: ArrayBuffer) => ipcRenderer.invoke('file:saveAs', name, bytes),
  dragOut: (file: unknown) => ipcRenderer.send('file:dragOut', file),
},
```

- [ ] **Step 5: Verify drag-out and commit**

In `FileTable` usage (DriveScreen), pass `onDragStart={(f, e) => { e.preventDefault(); window.minidrive.file.dragOut(f); }}`. Run the app: drag a row onto the Desktop → the file appears there (first drag of a large file may need a second attempt while it caches; small files work immediately).

```bash
git add apps/desktop
git commit -m "feat(desktop): folder binding, sync ipc, watcher and drag-out"
```

---

### Task 18: Renderer — SyncPanel

**Files:**
- Create: `apps/desktop/src/renderer/src/components/SyncPanel.tsx`
- Modify: `apps/desktop/src/renderer/src/screens/DriveScreen.tsx`

**Interfaces:**
- `SyncPanel` props `{ onSynced: () => void }`; shows bound folder path, «Прив'язати папку» / «Змінити», «Синхронізувати», the «Автоматично відстежувати зміни» checkbox, a progress line `done/total`, and the last `SyncReport` («Завантажено N, вивантажено M, пропущено K, помилок F»).

- [ ] **Step 1: Implement**

```tsx
import { useEffect, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const [folder, setFolder] = useState<string | null>(null);
  const [autoWatch, setAutoWatch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.minidrive.sync.status().then((s) => {
      setFolder(s.boundFolder);
      setAutoWatch(s.autoWatch);
    });
    const offProgress = window.minidrive.sync.onProgress(setProgress);
    const offAuto = window.minidrive.sync.onAutoSync((r) => {
      setReport(r as SyncReport);
      onSynced();
    });
    return () => {
      offProgress();
      offAuto();
    };
  }, [onSynced]);

  async function pick() {
    const chosen = await window.minidrive.folder.pick();
    if (chosen) setFolder(chosen);
  }

  async function sync() {
    if (!folder) return pick();
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      setReport(await window.minidrive.sync.run());
      onSynced();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleWatch(enabled: boolean) {
    setAutoWatch(await window.minidrive.sync.watch(enabled));
  }

  return (
    <section className="sync">
      <div className="folder">
        <span>{folder ?? "Папку не прив'язано"}</span>
        <button type="button" onClick={pick}>{folder ? 'Змінити' : "Прив'язати папку"}</button>
      </div>
      <div className="actions">
        <button type="button" onClick={sync} disabled={busy}>Синхронізувати</button>
        <label>
          <input type="checkbox" checked={autoWatch} disabled={!folder} onChange={(e) => toggleWatch(e.target.checked)} />
          Автоматично відстежувати зміни
        </label>
      </div>
      {busy && progress && <p>Передано {progress.done} з {progress.total}</p>}
      {error && <p className="error">{error}</p>}
      {report && (
        <p className="report">
          Завантажено {report.uploaded}, вивантажено {report.downloaded}, пропущено {report.skipped}, помилок {report.failed}
          {report.errors.length > 0 && <span> — {report.errors.join('; ')}</span>}
        </p>
      )}
    </section>
  );
}
```

Add `<SyncPanel onSynced={refresh} />` under the toolbar in `DriveScreen` (wrap `refresh` in `useCallback` in `useDrive` already done).

- [ ] **Step 2: Verify end to end, commit**

Checklist: bind a folder containing `a.cpp`; click «Синхронізувати» → `a.cpp` appears in the table and the remote files appear in the folder with the remote modification time; edit `a.cpp` locally and sync again → «Змінено» updates and «Редагував» shows the current user; enable auto-watch, drop a file into the folder → within ~2 s it appears in the table.

```bash
git add apps/desktop/src
git commit -m "feat(desktop): sync panel with folder binding and auto watch"
```

---

## Part D — Tests, packaging, report

### Task 19: Test run, packaging, screenshots and the Stage 2 report

**Files:**
- Create: `docs/reports/stage2-desktop.md`, `docs/reports/img/` (screenshots), `tools/screenshots.md` (list of shots to take)
- Modify: `README.md`, `docs/superpowers/specs/2026-09-07-minidrive-design.md` (line "Monorepo (yarn workspaces)…" → "npm workspaces")

**Interfaces:**
- Consumes everything above.

- [ ] **Step 1: Full test run**

Run: `yarn test` from the root.
Expected: shared 16 tests, api 8 tests, desktop 3 tests — all PASS. Record the console output for the report (`yarn test 2>&1 | tee docs/reports/img/tests.txt`).

- [ ] **Step 2: Package the desktop app**

Run: `yarn workspace @minidrive/desktop` build:mac (electron-builder from the template).
Expected: `apps/desktop/dist/*.dmg` (or `.app`). On failure related to code signing, add `"mac": { "identity": null }` to the `build` section of `apps/desktop/package.json`.

- [ ] **Step 3: Screenshots**

Spaces are per user and there is no sharing, so in a personal space «Завантажив» and «Редагував» normally show the owner. The report says so explicitly and still shows both columns. Log in as `bohdan`, upload `Program.cs`, `photo.jpg`, `main.cpp`, `logo.png`, `notes.txt`, `archive.zip`, then re-upload `Program.cs` so «Змінено» differs from «Створено».

Take and save under `docs/reports/img/`:
1. `01-login.png` — login screen with the server address field.
2. `02-table.png` — table with all columns, sorted ascending.
3. `03-sort-desc.png` — sorted descending.
4. `04-filter.png` — filter «Лише .cpp, .png».
5. `05-columns.png` — several columns hidden, «Назва» visible.
6. `06-preview-cs.png` — `.cs` file previewed as text.
7. `07-preview-jpg.png` — `.jpg` previewed as image.
8. `08-dragdrop.png` — the drop hint while dragging files in.
9. `09-sync.png` — sync panel with a report line.
10. `10-swagger.png` — `http://localhost:3000/docs`.
11. `11-tests.png` — terminal with `yarn test` output.
12. `12-docker.png` — `docker compose ps` showing the three services.

- [ ] **Step 4: Stage 2 report**

`docs/reports/stage2-desktop.md`, same front matter style as `stage1-uml.md` (title «Розробка клієнта для взаємодії з віддаленою папкою з файлами. Етап 2, варіант 4-6», subtitle «Десктоп-версія (Electron) та сервер (NestJS)», author «Виконав: студент групи МІ-41 Петров Богдан»). Sections:
1. Постановка задачі (short, refer to stage 1).
2. Архітектура реалізації — monorepo layout, `packages/shared`, API modules, desktop processes; how they map to the stage 1 diagrams (рис. 1, 6, 7 of stage 1).
3. Сервер — REST table, Prisma schema, storage keys, overwrite rule, Docker Compose (screenshot 12, 10).
4. Десктоп-клієнт — each function with a screenshot (1–9) and one paragraph: login/server address, table and attributes, sort by name (variant), filter (variant), columns, preview `.cs`/`.jpg` (variant), upload button and drag-and-drop (bonus), download and drag-out (bonus), delete, folder binding, sync and auto-watch, sync rules.
5. Unit-тестування — table: test file → what it checks → count; quote the variant tests (`sortByName`, `filterByType`, `DriveViewModel`) and the sync engine test; screenshot 11.
6. Інструкція із запуску — `corepack enable`, `yarn install`, `yarn stack:up`, `yarn workspace @minidrive/api db:seed`, `yarn workspace @minidrive/desktop dev`; env variables; how to point the client at a remote server (server address field / `MINIDRIVE_API_URL`).
7. Висновки.

Build: `tools/build-report.sh docs/reports/stage2-desktop.md`.

- [ ] **Step 5: README and spec touch-ups, final commit**

Update `README.md` run section to match Step 4.6.

```bash
git add README.md docs
git commit -m "docs: stage 2 report and run instructions"
```

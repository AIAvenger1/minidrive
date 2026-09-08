# Stage 3 (web client) and Stage 4 (comparison) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the Next.js web client of MiniDrive on top of the existing API and shared packages, prepare a production deployment (Caddy + Docker Compose + CI), write the Stage 3 report, then write the Stage 4 comparison report.

**Architecture:** `apps/web` is a Next.js App Router application whose pages are client components reusing `@minidrive/ui` and `@minidrive/shared` unchanged. The drive screen and the login form move from the desktop renderer into `packages/ui` (`DriveWorkspace`, `LoginForm`) so both clients render the same code and only inject platform behaviour (save file, drag-out, sync panel). Browser folder sync uses the File System Access API and a small "sync ledger" kept in `localStorage`, because a browser cannot set file modification times.

**Tech Stack:** Next.js (latest, App Router, `src/`, standalone output), React 19, Tailwind v4 via `@tailwindcss/postcss`, Vitest, Docker Compose + Caddy, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-minidrive-design.md` (§1 requirements, §3.3–§3.4 shared/web, §4.2 sync, §6 deployment, §7 testing).

**Branch:** all work on `stage3` (branched from `stage2` at 46a7d3c). Never push, never merge into `main`.

## Global Constraints

- Names from the spec are used verbatim: `FileTable`, `ColumnToggle`, `SortControl`, `FilterControl`, `PreviewPanel`, `UploadDropzone`, `SyncPanel`, `ApiClient`, `SessionStore`, `BrowserSyncEngine`, `DriveViewModel`, `FileDto`, `UserDto`, `AuthResponseDto`, `LocalFileInfo`, `SyncReport`, `computeSyncPlan`.
- REST routes exactly: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `GET /files`, `POST /files` (multipart field `file`), `GET /files/:id/content`, `DELETE /files/:id`. The API is not changed in this plan except for the `SWAGGER_ENABLED` flag (Task 6).
- Requirements R1–R9 of the spec apply to the web client: login/register, table with name/created/modified/uploaded by/modified by (+ size, type), hide/show every column except name, sort by name asc/desc, filter all / only `.cpp` and `.png`, preview `.cs` as text and `.jpg` as image, upload/download/delete, folder sync (bind folder, then sync; no automatic watching in the browser), drag-and-drop upload.
- Sync rules (spec §4.2): only local → upload; only remote → download; both with same size and |mtime − updatedAt| ≤ 2000 ms → skip; otherwise newest wins; deletions never propagate. **Accepted deviation for the browser:** after a transfer the browser records `{size, mtime, updatedAt}` in a sync ledger instead of setting the local mtime; on the next scan an unchanged file (same size and mtime as recorded) is treated as having mtime = `updatedAt`.
- **Code style: no comments in code. No docstrings. No "generated" markers. Clear names instead. The code must read as human-written.** Commit messages: `type(scope): lowercase summary`; end the body with a blank line then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Package manager: Yarn 4.9.1 via corepack (`nodeLinker: node-modules`; never PnP; never `npm`/`npx` in scripts). Node 22. All packages private. Workspace dependencies use `workspace:*`. React `^19.2.1` everywhere.
- `packages/ui` and `packages/shared` must not import from `electron`, `window.minidrive`, `next/*` or Node built-ins; platform-specific behaviour is passed in as props or constructor arguments. Components in `packages/ui` are rendered only inside client components on the web.
- Web dev server runs on port 3001 (the API owns 3000). The web reads the API base URL from `NEXT_PUBLIC_API_URL` (default `http://localhost:3000`) and stores the JWT in `localStorage` under `minidrive.token`.
- UI copy is Ukrainian, matching the desktop: «Увійти», «Зареєструватися», «Оновити», «Скачати», «Видалити», «Вийти», «Усі файли», «Лише .cpp, .png», «Синхронізувати», «Обрати папку».
- Reports are Ukrainian Markdown built with `tools/build-report.sh` into DOCX + PDF; built reports are committed. Author line: «Виконав: студент групи МІ-41 Петров Богдан».
- Screenshots are taken against the real running stack; nothing is mocked in a screenshot except, for the browser sync panel, an in-memory folder injected in place of the directory picker (headless Chrome cannot show one). Tooling/scratch scripts never enter the repo.
- Never run `git push`, never rewrite history, never `git clean`, never merge into `main`, never deploy to a remote host.

---

## File structure

```
packages/shared/src/syncLedger.ts            SyncLedger type + reconcileWithLedger/recordTransfer/pruneLedger (Task 1)
packages/ui/src/apiRegistry.ts               configureApi/getApi (moved from desktop) (Task 3)
packages/ui/src/LoginForm.tsx                shared login/register form (Task 3)
packages/ui/src/DriveWorkspace.tsx           shared drive screen (Task 4)
packages/ui/src/styles.css                   + .login/.drive/.drive-body layout rules (Task 3)
apps/web/                                    Next.js app (Task 2)
  package.json, next.config.ts, tsconfig.json, postcss.config.mjs, next-env.d.ts, vitest.config.ts, .env.example, public/favicon.svg
  src/app/layout.tsx, page.tsx, globals.css
  src/app/login/page.tsx                     (Task 3)
  src/app/drive/page.tsx                     (Task 4)
  src/lib/session.ts, src/hooks/useSession.ts (Task 3)
  src/lib/download.ts                        (Task 4)
  src/lib/browserSync.ts, src/lib/browserSync.test.ts, src/lib/syncLedgerStore.ts, src/components/SyncPanel.tsx (Task 5)
docker/web.Dockerfile, docker/compose.prod.yml, docker/Caddyfile, docker/.env.prod.example (Task 6)
.github/workflows/ci.yml                     (Task 6)
docs/uml/gen/05_class_clients.py (+ regenerated drawio/png/svg)   (Task 7)
docs/reports/stage3-web.md (+docx/pdf), docs/reports/img/web-*.png (Task 8)
docs/reports/stage4-comparison.md (+docx/pdf)                   (Task 9)
```

Parallelism: Task 1 → Task 2 → then three tracks: A = Tasks 3 → 4 → 5 (web features), B = Task 6 (deployment + CI), C = Task 7 (UML). Task 8 after A and B. Task 9 after Task 8.

---

### Task 1: Sync ledger in `packages/shared`

**Files:**
- Create: `packages/shared/src/syncLedger.ts`
- Create: `packages/shared/src/syncLedger.test.ts`
- Modify: `packages/shared/src/index.ts` (add `export * from './syncLedger';`)

**Interfaces:**
- Consumes: `LocalFileInfo` from `./types`.
- Produces: `SyncLedgerEntry = { size: number; mtime: number; updatedAt: string }`, `SyncLedger = Record<string, SyncLedgerEntry>`, `reconcileWithLedger(local: LocalFileInfo[], ledger: SyncLedger): LocalFileInfo[]`, `recordTransfer(ledger: SyncLedger, name: string, entry: SyncLedgerEntry): SyncLedger`, `pruneLedger(ledger: SyncLedger, present: LocalFileInfo[]): SyncLedger`.

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, expect, it } from 'vitest';
import { pruneLedger, reconcileWithLedger, recordTransfer, type SyncLedger } from './syncLedger';

const updatedAt = '2026-09-08T10:00:00.000Z';

describe('reconcileWithLedger', () => {
  it('replaces mtime with the recorded updatedAt when size and mtime match the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 10, mtime: 5000 }], ledger);
    expect(out).toEqual([{ name: 'a.cpp', size: 10, mtime: Date.parse(updatedAt) }]);
  });

  it('leaves a file alone when its size differs from the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 11, mtime: 5000 }], ledger);
    expect(out[0].mtime).toBe(5000);
  });

  it('leaves a file alone when its mtime differs from the ledger', () => {
    const ledger: SyncLedger = { 'a.cpp': { size: 10, mtime: 5000, updatedAt } };
    const out = reconcileWithLedger([{ name: 'a.cpp', size: 10, mtime: 6000 }], ledger);
    expect(out[0].mtime).toBe(6000);
  });

  it('leaves files without a ledger entry alone and does not mutate the input', () => {
    const input = [{ name: 'b.png', size: 3, mtime: 1 }];
    const out = reconcileWithLedger(input, {});
    expect(out).toEqual(input);
    expect(out).not.toBe(input);
  });
});

describe('recordTransfer', () => {
  it('returns a new ledger with the entry added and keeps the old one untouched', () => {
    const before: SyncLedger = {};
    const after = recordTransfer(before, 'a.cpp', { size: 1, mtime: 2, updatedAt });
    expect(after['a.cpp']).toEqual({ size: 1, mtime: 2, updatedAt });
    expect(before).toEqual({});
  });
});

describe('pruneLedger', () => {
  it('drops entries whose file is no longer present', () => {
    const ledger: SyncLedger = {
      'a.cpp': { size: 1, mtime: 2, updatedAt },
      'gone.txt': { size: 1, mtime: 2, updatedAt },
    };
    expect(Object.keys(pruneLedger(ledger, [{ name: 'a.cpp', size: 1, mtime: 2 }]))).toEqual(['a.cpp']);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `yarn workspace @minidrive/shared test`
Expected: FAIL, `Cannot find module './syncLedger'`.

- [ ] **Step 3: Implement**

```ts
import type { LocalFileInfo } from './types';

export type SyncLedgerEntry = { size: number; mtime: number; updatedAt: string };
export type SyncLedger = Record<string, SyncLedgerEntry>;

export function reconcileWithLedger(local: LocalFileInfo[], ledger: SyncLedger): LocalFileInfo[] {
  return local.map((file) => {
    const entry = ledger[file.name];
    if (!entry || entry.size !== file.size || entry.mtime !== file.mtime) return { ...file };
    return { ...file, mtime: Date.parse(entry.updatedAt) };
  });
}

export function recordTransfer(ledger: SyncLedger, name: string, entry: SyncLedgerEntry): SyncLedger {
  return { ...ledger, [name]: entry };
}

export function pruneLedger(ledger: SyncLedger, present: LocalFileInfo[]): SyncLedger {
  const names = new Set(present.map((file) => file.name));
  return Object.fromEntries(Object.entries(ledger).filter(([name]) => names.has(name)));
}
```

Add `export * from './syncLedger';` to `packages/shared/src/index.ts`.

- [ ] **Step 4: Run the tests and the build**

Run: `yarn workspace @minidrive/shared test && yarn workspace @minidrive/shared build`
Expected: 47 tests pass (41 + 6), build OK.

- [ ] **Step 5: Commit**

```bash
git add packages/shared/src/syncLedger.ts packages/shared/src/syncLedger.test.ts packages/shared/src/index.ts
git commit -m "feat(shared): sync ledger for clients that cannot set mtime"
```

---

### Task 2: Scaffold `apps/web` (Next.js) wired to the shared packages

**Files:**
- Create: `apps/web/package.json`, `apps/web/next.config.ts`, `apps/web/tsconfig.json`, `apps/web/postcss.config.mjs`, `apps/web/vitest.config.ts`, `apps/web/.env.example`, `apps/web/public/favicon.svg`, `apps/web/src/app/layout.tsx`, `apps/web/src/app/page.tsx`, `apps/web/src/app/globals.css`
- Modify: `packages/ui/src/theme.css` (add `@source "../../../apps/web/src";` after the desktop `@source` line)
- Modify: every file under `packages/ui/src` that imports with the `@/` alias → relative imports; remove the `@/*` alias from `apps/desktop/tsconfig.web.json` and `apps/desktop/electron.vite.config.ts`
- Modify: root `package.json` (add script `"web:dev": "yarn workspace @minidrive/web dev"`), `docker/api.Dockerfile` (add `COPY apps/web/package.json apps/web/` after the desktop manifest line)
- Modify: `README.md` (one paragraph: how to run the web client)

**Interfaces:**
- Produces: workspace `@minidrive/web` with scripts `dev` (port 3001), `build`, `start`, `typecheck`, `test`; `src/app/layout.tsx` root layout with `lang="uk"`; `/` redirects to `/drive`.

- [ ] **Step 1: Remove the `@/` alias dependency from `packages/ui`**

Run: `grep -rn "from '@/" packages/ui/src` — rewrite every hit to a relative import (for example in `packages/ui/src/components/ui/button.tsx` `import { cn } from '@/lib/utils'` becomes `import { cn } from '../../lib/utils'`). Then delete the `"@/*"` entry from `paths` in `apps/desktop/tsconfig.web.json` and the matching `'@'` alias in `apps/desktop/electron.vite.config.ts`. Leave `packages/ui/components.json` as it is (it only steers the shadcn CLI).

Run: `yarn workspace @minidrive/desktop typecheck` — Expected: clean.

- [ ] **Step 2: Create the workspace manifest**

`apps/web/package.json`:

```json
{
  "name": "@minidrive/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3001",
    "build": "next build",
    "start": "next start -p 3001",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@minidrive/shared": "workspace:*",
    "@minidrive/ui": "workspace:*",
    "lucide-react": "^1.42.0",
    "react": "^19.2.1",
    "react-dom": "^19.2.1"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.3.3",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.2.7",
    "tailwindcss": "^4.3.3",
    "typescript": "^5.6.0",
    "vitest": "^5.0.0"
  }
}
```

Then run `yarn workspace @minidrive/web add next@latest` so Yarn pins the current Next release with a caret range, and `yarn install`. If `yarn install` reformats other `package.json` files, revert those formatting-only changes.

- [ ] **Step 3: Configuration files**

`apps/web/next.config.ts`:

```ts
import path from 'path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(process.cwd(), '../..'),
  transpilePackages: ['@minidrive/shared', '@minidrive/ui'],
};

export default nextConfig;
```

`apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "src/**/*.ts", "src/**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

`apps/web/postcss.config.mjs`:

```js
export default { plugins: { '@tailwindcss/postcss': {} } };
```

`apps/web/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({ test: { include: ['src/**/*.test.ts'] } });
```

`apps/web/.env.example`:

```
NEXT_PUBLIC_API_URL=http://localhost:3000
```

`apps/web/public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1f2937"/><path d="M8 11h16v3H8zm0 7h16v3H8z" fill="#f9fafb"/></svg>
```

- [ ] **Step 4: App shell**

`apps/web/src/app/globals.css`:

```css
@import '@minidrive/ui/src/styles.css';
```

`apps/web/src/app/layout.tsx`:

```tsx
import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'MiniDrive',
  description: 'Легкий клієнт віддаленої папки з файлами',
  icons: '/favicon.svg',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="uk">
      <body>{children}</body>
    </html>
  );
}
```

`apps/web/src/app/page.tsx`:

```tsx
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/drive');
}
```

Add `@source "../../../apps/web/src";` to `packages/ui/src/theme.css` directly under the desktop `@source` line.

- [ ] **Step 5: Root wiring**

Root `package.json` scripts: add `"web:dev": "yarn workspace @minidrive/web dev"`. `docker/api.Dockerfile`: add `COPY apps/web/package.json apps/web/` right after `COPY apps/desktop/package.json apps/desktop/`. README: add a short «Веб-клієнт» paragraph (`cp apps/web/.env.example apps/web/.env.local`, `yarn web:dev`, open `http://localhost:3001`).

- [ ] **Step 6: Verify**

Run: `yarn workspace @minidrive/shared build && yarn workspace @minidrive/web typecheck && yarn workspace @minidrive/web build`
Expected: build succeeds; `apps/web/.next/standalone/apps/web/server.js` exists. `next-env.d.ts` is generated — commit it. Then `yarn workspace @minidrive/desktop typecheck && yarn workspace @minidrive/desktop build` still pass. Then `docker build -f docker/api.Dockerfile -t minidrive-api-check .` succeeds (the Dockerfile now copies the web manifest).

- [ ] **Step 7: Commit**

```bash
git add apps/web packages/ui/src apps/desktop/tsconfig.web.json apps/desktop/electron.vite.config.ts package.json yarn.lock docker/api.Dockerfile README.md
git commit -m "feat(web): scaffold next.js client on the shared packages"
```

---

### Task 3: Shared `LoginForm` + API registry, web session and `/login` page

**Files:**
- Create: `packages/ui/src/apiRegistry.ts`, `packages/ui/src/LoginForm.tsx`
- Modify: `packages/ui/src/index.ts` (export both), `packages/ui/src/styles.css` (append the layout rules below)
- Modify: `apps/desktop/src/renderer/src/screens/LoginScreen.tsx` (becomes a wrapper), `apps/desktop/src/renderer/src/session.ts`, `apps/desktop/src/renderer/src/App.tsx`, `apps/desktop/src/renderer/src/screens/DriveScreen.tsx` (import `configureApi`/`getApi` from `@minidrive/ui`)
- Delete: `apps/desktop/src/renderer/src/api.ts`, `apps/desktop/src/renderer/src/styles.css` (and its import in `apps/desktop/src/renderer/src/main.tsx`)
- Create: `apps/web/src/lib/session.ts`, `apps/web/src/hooks/useSession.ts`, `apps/web/src/app/login/page.tsx`

**Interfaces:**
- Consumes: `ApiClient`, `ApiError`, `AuthResponseDto`, `UserDto` from `@minidrive/shared`; ui primitives.
- Produces: `configureApi(baseUrl: string, token: string | null): ApiClient`, `getApi(): ApiClient`; `LoginForm` with props `{ apiUrl: string; allowServerChange?: boolean; onAuthenticated: (result: AuthResponseDto, apiUrl: string) => Promise<void> | void }`; web `SessionStore = { load(): string | null; save(token: string): void; clear(): void }`, `API_URL`; `useSession(): { user: UserDto | null; ready: boolean; logout: () => void }`.

- [ ] **Step 1: Move the API registry into `packages/ui`**

`packages/ui/src/apiRegistry.ts` (content identical to the current `apps/desktop/src/renderer/src/api.ts`):

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

Delete `apps/desktop/src/renderer/src/api.ts`; update `session.ts`, `App.tsx`, `screens/DriveScreen.tsx`, `screens/LoginScreen.tsx` to import `configureApi`/`getApi` from `@minidrive/ui`.

- [ ] **Step 2: Shared `LoginForm`**

`packages/ui/src/LoginForm.tsx` — the current desktop form, with the server field optional:

```tsx
import { useState, type FormEvent } from 'react';
import { ApiError, type AuthResponseDto } from '@minidrive/shared';
import { CircleAlert } from 'lucide-react';
import { configureApi } from './apiRegistry';
import { Alert, AlertDescription } from './components/ui/alert';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';

type Props = {
  apiUrl: string;
  allowServerChange?: boolean;
  onAuthenticated: (result: AuthResponseDto, apiUrl: string) => Promise<void> | void;
};

export function LoginForm({ apiUrl: initialApiUrl, allowServerChange = false, onAuthenticated }: Props) {
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const api = configureApi(apiUrl, null);
      const result = mode === 'login' ? await api.login(username, password) : await api.register(username, password);
      await onAuthenticated(result, api.baseUrl);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Сервер недоступний');
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setMode(mode === 'login' ? 'register' : 'login');
    setError(null);
  }

  return (
    <Card className="w-[360px]">
      <CardHeader>
        <CardTitle className="text-xl">MiniDrive</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={submit}>
          {allowServerChange ? (
            <div className="grid gap-1.5">
              <Label htmlFor="apiUrl">Адреса сервера</Label>
              <Input
                id="apiUrl"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:3000"
                required
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Сервер: {apiUrl}</p>
          )}
          <div className="grid gap-1.5">
            <Label htmlFor="username">Ім'я користувача</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <Alert variant="destructive" aria-live="polite">
              <CircleAlert />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" disabled={busy}>
            {mode === 'login' ? 'Увійти' : 'Зареєструватися'}
          </Button>
          <Button type="button" variant="link" onClick={switchMode}>
            {mode === 'login' ? 'Немає облікового запису? Зареєструватися' : 'Уже є обліковий запис? Увійти'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

Add to `packages/ui/src/index.ts`: `export * from './apiRegistry';` and `export * from './LoginForm';`.

Append to `packages/ui/src/styles.css` (moved verbatim from the desktop stylesheet, which is then deleted together with its import in `main.tsx`):

```css
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drive {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100vh;
  padding: 12px;
}
.drive-body {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  min-height: 0;
  flex: 1;
}
.drive-body > * {
  min-height: 0;
  overflow: auto;
}
```

Desktop `screens/LoginScreen.tsx` becomes:

```tsx
import type { UserDto } from '@minidrive/shared';
import { LoginForm } from '@minidrive/ui';
import { SessionStore } from '../session';

type Props = { apiUrl: string; onLoggedIn: (user: UserDto) => void };

export function LoginScreen({ apiUrl, onLoggedIn }: Props) {
  return (
    <div className="login">
      <LoginForm
        apiUrl={apiUrl}
        allowServerChange
        onAuthenticated={async (result, url) => {
          await SessionStore.save(result.accessToken, url);
          onLoggedIn(result.user);
        }}
      />
    </div>
  );
}
```

Run: `yarn workspace @minidrive/desktop typecheck && yarn workspace @minidrive/desktop build` — Expected: clean. Launch `env -u ELECTRON_RUN_AS_NODE yarn workspace @minidrive/desktop dev` once and confirm the login card renders centred as before, then quit it.

- [ ] **Step 3: Web session**

`apps/web/src/lib/session.ts`:

```ts
import { configureApi } from '@minidrive/ui';

const TOKEN_KEY = 'minidrive.token';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3000';

export const SessionStore = {
  load(): string | null {
    const token = window.localStorage.getItem(TOKEN_KEY);
    configureApi(API_URL, token);
    return token;
  },
  save(token: string) {
    window.localStorage.setItem(TOKEN_KEY, token);
    configureApi(API_URL, token);
  },
  clear() {
    window.localStorage.removeItem(TOKEN_KEY);
    configureApi(API_URL, null);
  },
};
```

`apps/web/src/hooks/useSession.ts`:

```ts
import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { UserDto } from '@minidrive/shared';
import { getApi } from '@minidrive/ui';
import { SessionStore } from '../lib/session';

export function useSession() {
  const router = useRouter();
  const [user, setUser] = useState<UserDto | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!SessionStore.load()) {
      router.replace('/login');
      return;
    }
    getApi()
      .me()
      .then(setUser)
      .catch(() => {
        SessionStore.clear();
        router.replace('/login');
      })
      .finally(() => setReady(true));
  }, [router]);

  const logout = useCallback(() => {
    SessionStore.clear();
    router.replace('/login');
  }, [router]);

  return { user, ready, logout };
}
```

- [ ] **Step 4: `/login` page**

`apps/web/src/app/login/page.tsx`:

```tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoginForm } from '@minidrive/ui';
import { API_URL, SessionStore } from '../../lib/session';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    if (SessionStore.load()) router.replace('/drive');
  }, [router]);

  return (
    <main className="login">
      <LoginForm
        apiUrl={API_URL}
        onAuthenticated={(result) => {
          SessionStore.save(result.accessToken);
          router.replace('/drive');
        }}
      />
    </main>
  );
}
```

- [ ] **Step 5: Verify**

Run: `yarn workspace @minidrive/web typecheck && yarn workspace @minidrive/web build`. Then, with the Docker stack up (`docker compose -f docker/compose.yml ps` shows api healthy), start `yarn web:dev`, open `http://localhost:3001/login`, log in as `bohdan` / `secret123`: the page navigates to `/drive` (404 for now is expected) and `localStorage['minidrive.token']` is set. Stop the dev server.

- [ ] **Step 6: Commit**

```bash
git add packages/ui/src apps/desktop/src/renderer apps/web/src
git commit -m "feat(ui,web): shared login form and web session"
```

---

### Task 4: Shared `DriveWorkspace` and the web `/drive` page

**Files:**
- Create: `packages/ui/src/DriveWorkspace.tsx`
- Modify: `packages/ui/src/index.ts` (export it)
- Modify: `apps/desktop/src/renderer/src/screens/DriveScreen.tsx` (becomes a wrapper)
- Create: `apps/web/src/lib/download.ts`, `apps/web/src/app/drive/page.tsx`

**Interfaces:**
- Consumes: `useDrive`, `FileTable`, `SortControl`, `FilterControl`, `ColumnToggle`, `PreviewPanel`, `UploadDropzone`, dialog/button/badge primitives; `getApi`.
- Produces: `DriveWorkspace` with props
  `{ user: UserDto; api: ApiClient; onLogout: () => void; saveFile: (file: FileDto, blob: Blob) => Promise<void> | void; onRowDragStart?: (file: FileDto, e: React.DragEvent) => void; subscribeErrors?: (report: (message: string) => void) => () => void; renderSyncPanel?: (onSynced: () => void) => ReactNode }`.

- [ ] **Step 1: `DriveWorkspace` in `packages/ui`**

```tsx
import { useCallback, useEffect, useState, type DragEvent, type ReactNode } from 'react';
import type { ApiClient, FileDto, UserDto } from '@minidrive/shared';
import { ColumnToggle } from './ColumnToggle';
import { FileTable } from './FileTable';
import { FilterControl } from './FilterControl';
import { PreviewPanel } from './PreviewPanel';
import { SortControl } from './SortControl';
import { UploadDropzone } from './UploadDropzone';
import { useDrive } from './useDrive';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './components/ui/dialog';

type Props = {
  user: UserDto;
  api: ApiClient;
  onLogout: () => void;
  saveFile: (file: FileDto, blob: Blob) => Promise<void> | void;
  onRowDragStart?: (file: FileDto, e: DragEvent) => void;
  subscribeErrors?: (report: (message: string) => void) => () => void;
  renderSyncPanel?: (onSynced: () => void) => ReactNode;
};

export function DriveWorkspace({ user, api, onLogout, saveFile, onRowDragStart, subscribeErrors, renderSyncPanel }: Props) {
  const { vm, refresh, update, busy, error, setError } = useDrive(api, onLogout);
  const [working, setWorking] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => subscribeErrors?.(setError), [subscribeErrors, setError]);

  const loadContent = useCallback((f: FileDto) => api.download(f.id), [api]);

  async function run(action: () => Promise<void>) {
    setWorking(true);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorking(false);
    }
  }

  function uploadFiles(files: File[]) {
    return run(async () => {
      for (const f of files) await api.upload(f.name, f, f.type || 'application/octet-stream');
      await refresh();
    });
  }

  function downloadSelected() {
    const file = vm.selected;
    if (!file) return;
    return run(async () => {
      await saveFile(file, await api.download(file.id));
    });
  }

  function deleteSelected() {
    const file = vm.selected;
    if (!file) return;
    setConfirmDelete(false);
    return run(async () => {
      await api.remove(file.id);
      await refresh();
    });
  }

  return (
    <div className="drive">
      <header className="flex items-center gap-4">
        <strong>MiniDrive</strong>
        <Badge variant="secondary" className="ml-auto">
          {user.username}
        </Badge>
        <Button type="button" variant="ghost" onClick={onLogout}>
          Вийти
        </Button>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <SortControl order={vm.order} onChange={(o) => update((m) => m.setOrder(o))} />
        <FilterControl filter={vm.filter} onChange={(f) => update((m) => m.setFilter(f))} />
        <ColumnToggle columns={vm.columns} onToggle={(k) => update((m) => m.toggleColumn(k))} />
        <Button type="button" variant="outline" onClick={refresh} disabled={busy}>
          Оновити
        </Button>
        <Button type="button" variant="outline" onClick={downloadSelected} disabled={!vm.selected || working}>
          Скачати
        </Button>
        <Button type="button" variant="destructive" onClick={() => setConfirmDelete(true)} disabled={!vm.selected || working}>
          Видалити
        </Button>
      </div>
      {error && <p className="text-destructive">{error}</p>}
      {renderSyncPanel?.(refresh)}
      <div className="drive-body">
        <UploadDropzone onFiles={uploadFiles} busy={working}>
          <FileTable
            files={vm.visibleFiles}
            columns={vm.columns}
            selected={vm.selected}
            onSelect={(f) => update((m) => m.select(f))}
            onDragStart={onRowDragStart}
          />
        </UploadDropzone>
        <PreviewPanel file={vm.selected} loadContent={loadContent} />
      </div>
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Видалити файл?</DialogTitle>
            <DialogDescription>Файл буде видалено без можливості відновлення.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirmDelete(false)}>
              Скасувати
            </Button>
            <Button type="button" variant="destructive" onClick={deleteSelected}>
              Видалити
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

Add `export * from './DriveWorkspace';` to `packages/ui/src/index.ts`. Check `FileTable`'s `onDragStart` prop type is `(file: FileDto, e: React.DragEvent) => void` — keep them identical.

- [ ] **Step 2: Desktop wrapper**

`apps/desktop/src/renderer/src/screens/DriveScreen.tsx` becomes:

```tsx
import { useCallback } from 'react';
import type { FileDto, UserDto } from '@minidrive/shared';
import { DriveWorkspace, getApi } from '@minidrive/ui';
import { SyncPanel } from '../components/SyncPanel';

type Props = { user: UserDto; onLogout: () => void };

export function DriveScreen({ user, onLogout }: Props) {
  const saveFile = useCallback(async (file: FileDto, blob: Blob) => {
    await window.minidrive.file.saveAs(file.name, await blob.arrayBuffer());
  }, []);
  const subscribeErrors = useCallback(
    (report: (message: string) => void) => window.minidrive.file.onDragOutError(report),
    [],
  );

  return (
    <DriveWorkspace
      user={user}
      api={getApi()}
      onLogout={onLogout}
      saveFile={saveFile}
      onRowDragStart={(f, e) => {
        e.preventDefault();
        window.minidrive.file.dragOut(f);
      }}
      subscribeErrors={subscribeErrors}
      renderSyncPanel={(onSynced) => <SyncPanel onSynced={onSynced} />}
    />
  );
}
```

Run: `yarn workspace @minidrive/desktop typecheck && yarn workspace @minidrive/desktop test && yarn workspace @minidrive/desktop build` — Expected: clean, 7 tests. Launch the desktop app once against the running stack, log in, confirm the table, preview and «Скачати» still work, quit.

- [ ] **Step 3: Web download helper and `/drive` page**

`apps/web/src/lib/download.ts`:

```ts
export function saveBlob(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```

`apps/web/src/app/drive/page.tsx`:

```tsx
'use client';

import { DriveWorkspace, getApi } from '@minidrive/ui';
import { useSession } from '../../hooks/useSession';
import { saveBlob } from '../../lib/download';

export default function DrivePage() {
  const { user, ready, logout } = useSession();

  if (!ready || !user) return null;
  return (
    <DriveWorkspace
      user={user}
      api={getApi()}
      onLogout={logout}
      saveFile={(file, blob) => saveBlob(file.name, blob)}
    />
  );
}
```

- [ ] **Step 4: Verify in the browser**

Run: `yarn workspace @minidrive/web typecheck && yarn workspace @minidrive/web build`, then `yarn web:dev` against the running stack: log in as `bohdan`, upload a `.cs` and a `.jpg` through the file picker and by drag-and-drop, check sort, filter, column toggles, both previews, «Скачати» (browser download), «Видалити» with the dialog, «Вийти» returns to `/login`. Delete the test files afterwards. Stop the dev server.

- [ ] **Step 5: Commit**

```bash
git add packages/ui/src apps/desktop/src/renderer/src/screens/DriveScreen.tsx apps/web/src
git commit -m "feat(ui,web): shared drive workspace and web drive page"
```

---

### Task 5: `BrowserSyncEngine` and the web `SyncPanel`

**Files:**
- Create: `apps/web/src/lib/browserSync.ts`, `apps/web/src/lib/browserSync.test.ts`, `apps/web/src/lib/syncLedgerStore.ts`, `apps/web/src/components/SyncPanel.tsx`
- Modify: `apps/web/src/app/drive/page.tsx` (pass `renderSyncPanel`)

**Interfaces:**
- Consumes: `computeSyncPlan`, `emptySyncReport`, `isSyncableName`, `reconcileWithLedger`, `recordTransfer`, `pruneLedger`, `makeFileDto` (tests) from `@minidrive/shared`.
- Produces: `supportsFolderSync(): boolean`, `pickFolder(): Promise<DirectoryHandleLike>`, `class BrowserSyncEngine { constructor(api: SyncApi, ledgers: LedgerStore); scan(dir): Promise<LocalFileInfo[]>; synchronize(dir, onProgress?): Promise<SyncReport> }`, `localLedgerStore: LedgerStore`.

- [ ] **Step 1: Write the failing test**

`apps/web/src/lib/browserSync.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import { makeFileDto, type SyncLedger } from '@minidrive/shared';
import { BrowserSyncEngine, type DirectoryHandleLike, type FileHandleLike, type LedgerStore } from './browserSync';

function memoryFolder(name: string, files: Record<string, { content: string; lastModified: number }>) {
  const store = new Map(Object.entries(files));
  const handleFor = (fileName: string): FileHandleLike & { createWritable(): Promise<{ write(d: Blob): Promise<void>; close(): Promise<void> }> } => ({
    kind: 'file',
    name: fileName,
    async getFile() {
      const entry = store.get(fileName) ?? { content: '', lastModified: 0 };
      return new File([entry.content], fileName, { lastModified: entry.lastModified });
    },
    async createWritable() {
      let buffered = '';
      return {
        async write(data: Blob) {
          buffered = await data.text();
        },
        async close() {
          store.set(fileName, { content: buffered, lastModified: Date.now() });
        },
      };
    },
  });
  const dir: DirectoryHandleLike = {
    kind: 'directory',
    name,
    async *values() {
      for (const fileName of store.keys()) yield handleFor(fileName);
    },
    async getFileHandle(fileName, options) {
      if (!store.has(fileName) && !options?.create) throw new Error('not found');
      return handleFor(fileName);
    },
  };
  return { dir, store };
}

function memoryLedgers(initial: SyncLedger = {}): LedgerStore & { saved: SyncLedger } {
  const state = { saved: initial } as LedgerStore & { saved: SyncLedger };
  state.load = () => state.saved;
  state.save = (_folder, ledger) => {
    state.saved = ledger;
  };
  return state;
}

describe('BrowserSyncEngine', () => {
  it('uploads local-only files and downloads remote-only files, recording both in the ledger', async () => {
    const { dir, store } = memoryFolder('work', { 'local.cpp': { content: 'int main;', lastModified: 1000 } });
    const remote = makeFileDto({ id: 'r1', name: 'remote.png', size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
    const api = {
      listFiles: vi.fn(async () => [remote]),
      upload: vi.fn(async (name: string) => makeFileDto({ name, updatedAt: '2026-09-08T11:00:00.000Z' })),
      download: vi.fn(async () => new Blob(['png'])),
    };
    const ledgers = memoryLedgers();
    const report = await new BrowserSyncEngine(api, ledgers).synchronize(dir);

    expect(report).toMatchObject({ uploaded: 1, downloaded: 1, skipped: 0, failed: 0 });
    expect(api.upload).toHaveBeenCalledWith('local.cpp', expect.any(File), 'application/octet-stream');
    expect(store.get('remote.png')?.content).toBe('png');
    expect(ledgers.saved['local.cpp']).toMatchObject({ size: 9, mtime: 1000, updatedAt: '2026-09-08T11:00:00.000Z' });
    expect(ledgers.saved['remote.png']).toMatchObject({ size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
  });

  it('skips a file the ledger already knows, even though the browser could not set its mtime', async () => {
    const { dir } = memoryFolder('work', { 'same.cpp': { content: 'abc', lastModified: 5000 } });
    const remote = makeFileDto({ id: 'r1', name: 'same.cpp', size: 3, updatedAt: '2026-09-08T10:00:00.000Z' });
    const api = { listFiles: vi.fn(async () => [remote]), upload: vi.fn(), download: vi.fn() };
    const ledgers = memoryLedgers({ 'same.cpp': { size: 3, mtime: 5000, updatedAt: '2026-09-08T10:00:00.000Z' } });
    const report = await new BrowserSyncEngine(api, ledgers).synchronize(dir);

    expect(report).toMatchObject({ uploaded: 0, downloaded: 0, skipped: 1, failed: 0 });
    expect(api.upload).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
  });

  it('counts a failed transfer without aborting the rest and reports progress', async () => {
    const { dir } = memoryFolder('work', { 'a.cpp': { content: 'a', lastModified: 1 }, 'b.cpp': { content: 'b', lastModified: 1 } });
    const api = {
      listFiles: vi.fn(async () => []),
      upload: vi.fn(async (name: string) => {
        if (name === 'a.cpp') throw new Error('boom');
        return makeFileDto({ name });
      }),
      download: vi.fn(),
    };
    const progress: Array<[number, number]> = [];
    const report = await new BrowserSyncEngine(api, memoryLedgers()).synchronize(dir, (done, total) => progress.push([done, total]));

    expect(report).toMatchObject({ uploaded: 1, failed: 1 });
    expect(report.errors).toEqual(['a.cpp: boom']);
    expect(progress).toEqual([[1, 2], [2, 2]]);
  });

  it('ignores dot-prefixed and non-file entries when scanning', async () => {
    const { dir } = memoryFolder('work', { '.hidden': { content: 'x', lastModified: 1 }, 'ok.png': { content: 'y', lastModified: 1 } });
    const files = await new BrowserSyncEngine({ listFiles: vi.fn(), upload: vi.fn(), download: vi.fn() }, memoryLedgers()).scan(dir);
    expect(files.map((f) => f.name)).toEqual(['ok.png']);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `yarn workspace @minidrive/web test`
Expected: FAIL, `Cannot find module './browserSync'`.

- [ ] **Step 3: Implement the engine and the ledger store**

`apps/web/src/lib/browserSync.ts`:

```ts
import {
  computeSyncPlan,
  emptySyncReport,
  isSyncableName,
  pruneLedger,
  reconcileWithLedger,
  recordTransfer,
  type ApiClient,
  type FileDto,
  type LocalFileInfo,
  type SyncLedger,
  type SyncLedgerEntry,
  type SyncReport,
} from '@minidrive/shared';

export type WritableLike = { write(data: Blob): Promise<void>; close(): Promise<void> };
export type FileHandleLike = { kind: 'file'; name: string; getFile(): Promise<File> };
export type WritableFileHandleLike = FileHandleLike & { createWritable(): Promise<WritableLike> };
export type DirectoryHandleLike = {
  kind: 'directory';
  name: string;
  values(): AsyncIterable<FileHandleLike | DirectoryHandleLike>;
  getFileHandle(name: string, options?: { create?: boolean }): Promise<WritableFileHandleLike>;
};
export type SyncApi = Pick<ApiClient, 'listFiles' | 'upload' | 'download'>;
export type LedgerStore = { load(folder: string): SyncLedger; save(folder: string, ledger: SyncLedger): void };
type Progress = (done: number, total: number) => void;
type PickerWindow = { showDirectoryPicker(options: { mode: 'readwrite' }): Promise<DirectoryHandleLike> };

export function supportsFolderSync(): boolean {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

export function pickFolder(): Promise<DirectoryHandleLike> {
  return (window as unknown as PickerWindow).showDirectoryPicker({ mode: 'readwrite' });
}

export class BrowserSyncEngine {
  constructor(private readonly api: SyncApi, private readonly ledgers: LedgerStore) {}

  async scan(dir: DirectoryHandleLike): Promise<LocalFileInfo[]> {
    const files: LocalFileInfo[] = [];
    for await (const handle of dir.values()) {
      if (handle.kind !== 'file' || !isSyncableName(handle.name)) continue;
      const file = await handle.getFile();
      files.push({ name: handle.name, size: file.size, mtime: file.lastModified });
    }
    return files;
  }

  async synchronize(dir: DirectoryHandleLike, onProgress?: Progress): Promise<SyncReport> {
    const [scanned, remote] = await Promise.all([this.scan(dir), this.api.listFiles()]);
    let ledger = pruneLedger(this.ledgers.load(dir.name), scanned);
    const plan = computeSyncPlan(reconcileWithLedger(scanned, ledger), remote);
    const remoteByName = new Map(remote.map((r) => [r.name, r]));
    const report = emptySyncReport();
    report.skipped = plan.skipped.length;
    const total = plan.uploads.length + plan.downloads.length;
    let done = 0;

    for (const action of plan.uploads) {
      try {
        ledger = recordTransfer(ledger, action.name, await this.uploadFrom(dir, action.name));
        report.uploaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    for (const action of plan.downloads) {
      try {
        const dto = remoteByName.get(action.name);
        if (!dto) throw new Error('remote entry disappeared');
        ledger = recordTransfer(ledger, action.name, await this.downloadTo(dir, dto));
        report.downloaded += 1;
      } catch (err) {
        report.failed += 1;
        report.errors.push(`${action.name}: ${(err as Error).message}`);
      }
      onProgress?.(++done, total);
    }

    this.ledgers.save(dir.name, ledger);
    return report;
  }

  private async uploadFrom(dir: DirectoryHandleLike, name: string): Promise<SyncLedgerEntry> {
    const file = await (await dir.getFileHandle(name)).getFile();
    const dto = await this.api.upload(name, file, file.type || 'application/octet-stream');
    return { size: file.size, mtime: file.lastModified, updatedAt: dto.updatedAt };
  }

  private async downloadTo(dir: DirectoryHandleLike, file: FileDto): Promise<SyncLedgerEntry> {
    const blob = await this.api.download(file.id);
    const handle = await dir.getFileHandle(file.name, { create: true });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    const written = await handle.getFile();
    return { size: written.size, mtime: written.lastModified, updatedAt: file.updatedAt };
  }
}
```

`apps/web/src/lib/syncLedgerStore.ts`:

```ts
import type { SyncLedger } from '@minidrive/shared';
import type { LedgerStore } from './browserSync';

const PREFIX = 'minidrive.sync.';

export const localLedgerStore: LedgerStore = {
  load(folder) {
    try {
      return JSON.parse(window.localStorage.getItem(PREFIX + folder) ?? '{}') as SyncLedger;
    } catch {
      return {};
    }
  },
  save(folder, ledger) {
    window.localStorage.setItem(PREFIX + folder, JSON.stringify(ledger));
  },
};
```

- [ ] **Step 4: Run the tests**

Run: `yarn workspace @minidrive/web test` — Expected: 4 tests pass.

- [ ] **Step 5: Web `SyncPanel`**

`apps/web/src/components/SyncPanel.tsx`:

```tsx
'use client';

import { useMemo, useState } from 'react';
import type { SyncReport } from '@minidrive/shared';
import { Alert, AlertDescription, Button, Card, CardContent, Progress, getApi } from '@minidrive/ui';
import { BrowserSyncEngine, pickFolder, supportsFolderSync, type DirectoryHandleLike } from '../lib/browserSync';
import { localLedgerStore } from '../lib/syncLedgerStore';

export function SyncPanel({ onSynced }: { onSynced: () => void }) {
  const supported = useMemo(() => supportsFolderSync(), []);
  const [folder, setFolder] = useState<DirectoryHandleLike | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choose(): Promise<DirectoryHandleLike | null> {
    try {
      const chosen = await pickFolder();
      setFolder(chosen);
      setReport(null);
      return chosen;
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setError((err as Error).message);
      return null;
    }
  }

  async function sync() {
    const dir = folder ?? (await choose());
    if (!dir) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      const result = await new BrowserSyncEngine(getApi(), localLedgerStore).synchronize(dir, (done, total) =>
        setProgress({ done, total }),
      );
      setReport(result);
      onSynced();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!supported) {
    return (
      <Alert>
        <AlertDescription>Синхронізація папки недоступна в цьому браузері. Потрібен Chrome або Edge.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-3 pt-6">
        <span className="text-sm text-muted-foreground">{folder ? `Папка: ${folder.name}` : 'Папку не обрано'}</span>
        <Button type="button" variant="outline" onClick={choose} disabled={busy}>
          Обрати папку
        </Button>
        <Button type="button" onClick={sync} disabled={busy}>
          Синхронізувати
        </Button>
        {progress && progress.total > 0 && (
          <Progress className="w-40" value={(progress.done / progress.total) * 100} />
        )}
        {report && (
          <span className="text-sm">
            Завантажено {report.uploaded}, вивантажено {report.downloaded}, пропущено {report.skipped}, помилок{' '}
            {report.failed}
          </span>
        )}
        {error && (
          <Alert variant="destructive" className="w-full">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
```

Match the desktop wording exactly: open `apps/desktop/src/renderer/src/components/SyncPanel.tsx` and copy its report sentence («Завантажено … вивантажено … пропущено … помилок …») and its error rendering if they differ from the above.

In `apps/web/src/app/drive/page.tsx` add `renderSyncPanel={(onSynced) => <SyncPanel onSynced={onSynced} />}` (import from `../../components/SyncPanel`).

- [ ] **Step 6: Verify in Chrome**

Run: `yarn workspace @minidrive/web typecheck && yarn workspace @minidrive/web test && yarn workspace @minidrive/web build`. Then `yarn web:dev`, open in Chrome, log in, pick a scratch folder containing one `.cpp`, click «Синхронізувати»: report shows one upload; click again: everything skipped (the ledger works). Clean the uploaded file from the server afterwards. Stop the dev server.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src
git commit -m "feat(web): browser folder sync with a local ledger"
```

---

### Task 6: Production deployment files, API hardening flag, CI workflow

**Files:**
- Modify: `apps/api/src/config.ts` (+ `swaggerEnabled: boolean`), `apps/api/src/config.spec.ts` (or the existing config test file — add one case), `apps/api/src/main.ts` (guard Swagger setup), `apps/api/.env.example` (+ `SWAGGER_ENABLED=true`)
- Modify: `docker/compose.yml` (bind postgres and minio ports to `127.0.0.1`)
- Create: `docker/web.Dockerfile`, `docker/compose.prod.yml`, `docker/Caddyfile`, `docker/.env.prod.example`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md` (section «Розгортання (production)»)

**Interfaces:**
- Consumes: `apps/web` build (Task 2) with `output: 'standalone'` and `outputFileTracingRoot` = repo root.
- Produces: `docker compose -f docker/compose.prod.yml --env-file docker/.env.prod up -d --build` serving the web at `https://$DOMAIN/` and the API at `https://$DOMAIN/api/`.

- [ ] **Step 1: Swagger flag (test first)**

Add to the API config test file a case: with `SWAGGER_ENABLED=false` `loadConfig(env).swaggerEnabled` is `false`; unset → `true`. Implement in `config.ts`: `swaggerEnabled: (env.SWAGGER_ENABLED ?? 'true') !== 'false'`. In `main.ts` wrap the `DocumentBuilder`/`SwaggerModule.setup` block in `if (config.swaggerEnabled) { … }`. Add `SWAGGER_ENABLED=true` to `apps/api/.env.example`.

Run: `yarn workspace @minidrive/api test && yarn workspace @minidrive/api build` — Expected: pass.

- [ ] **Step 2: Dev compose ports**

In `docker/compose.yml` change `"5432:5432"` → `"127.0.0.1:5432:5432"`, `"9000:9000"` → `"127.0.0.1:9000:9000"`, `"9001:9001"` → `"127.0.0.1:9001:9001"`. Leave the API port as is.

- [ ] **Step 3: Web image**

`docker/web.Dockerfile`:

```dockerfile
FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json yarn.lock .yarnrc.yml tsconfig.base.json ./
COPY packages/shared/package.json packages/shared/
COPY packages/ui/package.json packages/ui/
COPY apps/api/package.json apps/api/
COPY apps/desktop/package.json apps/desktop/
COPY apps/web/package.json apps/web/
RUN yarn workspaces focus @minidrive/web @minidrive/shared @minidrive/ui
COPY packages/shared packages/shared
COPY packages/ui packages/ui
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN yarn workspace @minidrive/shared build && yarn workspace @minidrive/web build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=build /repo/apps/web/.next/standalone ./
COPY --from=build /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /repo/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
```

- [ ] **Step 4: Production compose and Caddy**

`docker/Caddyfile`:

```
{$DOMAIN} {
	handle_path /api/* {
		reverse_proxy api:3000
	}
	handle {
		reverse_proxy web:3000
	}
}
```

`docker/.env.prod.example`:

```
DOMAIN=localhost
POSTGRES_USER=minidrive
POSTGRES_PASSWORD=change-me
POSTGRES_DB=minidrive
MINIO_ROOT_USER=minidrive
MINIO_ROOT_PASSWORD=change-me-too
JWT_SECRET=change-me-in-production
```

`docker/compose.prod.yml`:

```yaml
name: minidrive-prod

services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    environment:
      DOMAIN: ${DOMAIN}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddydata:/data
      - caddyconfig:/config
    depends_on:
      - api
      - web

  web:
    build:
      context: ..
      dockerfile: docker/web.Dockerfile
      args:
        NEXT_PUBLIC_API_URL: https://${DOMAIN}/api
    depends_on:
      api:
        condition: service_healthy

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
      CORS_ORIGINS: https://${DOMAIN}
      SWAGGER_ENABLED: "false"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9000/minio/health/live || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
  miniodata:
  caddydata:
  caddyconfig:
```

- [ ] **Step 5: CI workflow**

`.github/workflows/ci.yml`:

```yaml
name: ci

on:
  push:
    branches: [main, stage2, stage3]
  pull_request:

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: corepack enable
      - run: yarn install --immutable
      - run: yarn build
      - run: yarn test
```

- [ ] **Step 6: Verify the production stack locally**

Run (from the repo root): `cp docker/.env.prod.example docker/.env.prod` (git-ignored by `.env.*`), then `docker compose -f docker/compose.prod.yml --env-file docker/.env.prod up -d --build --wait`. Expected: five containers up. `curl -sk https://localhost/api/health` returns the health JSON; `curl -sk https://localhost/ -o /dev/null -w '%{http_code}'` prints `200` and `curl -sk https://localhost/login | grep -c MiniDrive` is at least 1; `curl -sk https://localhost/api/docs -o /dev/null -w '%{http_code}'` prints `404` (Swagger off). Then `docker compose -f docker/compose.prod.yml --env-file docker/.env.prod down -v` and confirm the dev stack (`docker compose -f docker/compose.yml ps`) is still healthy.

README: add «Розгортання (production)» — copy `.env.prod.example` → `.env.prod`, set `DOMAIN` to the public hostname pointing at the VM, open ports 80/443, run the compose command above; the web is served at `https://DOMAIN`, the API at `https://DOMAIN/api`, and the desktop client uses `https://DOMAIN/api` as its server address. Mention CI runs build + tests on push.

- [ ] **Step 7: Commit**

```bash
git add apps/api/src apps/api/.env.example docker .github README.md
git commit -m "feat(deploy): production compose with caddy and web image, ci workflow"
```

---

### Task 7: Update the clients class diagram for the browser sync ledger

**Files:**
- Modify: `docs/uml/gen/05_class_clients.py`
- Regenerate: `docs/uml/drawio/05-class-clients.drawio`, `docs/uml/img/05-class-clients.png`, `docs/uml/img/05-class-clients.svg`

**Interfaces:**
- Consumes: `tools/drawio_gen/drawio.py` and `docs/uml/gen/_common.py` (read `tools/drawio_gen/README.md` for how a generator script is run and how PNG/SVG are exported with the `drawio` CLI at `/opt/homebrew/bin/drawio`).

- [ ] **Step 1: Edit the generator**

In the `packages/shared` group add a class `SyncLedger` with attrs `- entries: Map<name, {size, mtime, updatedAt}>` and methods `+ reconcileWithLedger(local, ledger)`, `+ recordTransfer(ledger, name, entry)`, `+ pruneLedger(ledger, present)`. Give `BrowserSyncEngine` the methods `+ scan(dir): LocalFileInfo[]` and `+ synchronize(dir): SyncReport` and a dependency edge `«use»` to `SyncLedger`. Change the web note text to `File System Access API (Chrome/Edge);\nno automatic watching;\nmtime kept in a localStorage ledger`. Give the web `SessionStore` methods `+ load()`, `+ save(token)`, `+ clear()`. Add a class `DriveWorkspace` and a class `LoginForm` (stereotype `component`, colour of the other shared UI components) in whichever group the generator uses for the shared React components; if the diagram has no such group, add them to the `apps/web` group with a note `shared via packages/ui`. Keep the layout free of overlaps (run the generator and open the PNG to check).

- [ ] **Step 2: Regenerate and check**

Run the generator the way the README describes, then export PNG (2x) and SVG. Open `docs/uml/img/05-class-clients.png` with the Read tool and confirm no overlapping labels; adjust `min_w` or ordering if needed.

- [ ] **Step 3: Commit**

```bash
git add docs/uml/gen/05_class_clients.py docs/uml/drawio/05-class-clients.drawio docs/uml/img/05-class-clients.png docs/uml/img/05-class-clients.svg
git commit -m "docs(uml): browser sync ledger and shared drive workspace on the clients diagram"
```

---

### Task 8: Stage 3 report, screenshots, DOCX/PDF

**Files:**
- Create: `docs/reports/stage3-web.md`, `docs/reports/stage3-web.docx`, `docs/reports/stage3-web.pdf`
- Create: `docs/reports/img/web-01-login.png` … `web-12-prod.png`, `docs/reports/img/web-tests.txt`
- Modify: `README.md` (link the Stage 3 report next to the others)

**Interfaces:**
- Consumes: running dev stack (`docker/compose.yml`), `yarn web:dev` on 3001, headless/CDP Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, `tools/build-report.sh`.

- [ ] **Step 1: Test run**

Run `yarn test 2>&1 | tee docs/reports/img/web-tests.txt` from the repo root; strip any line containing `/Users/`. Expected: shared 47, api 22, desktop 7, web 4.

- [ ] **Step 2: Screenshots (Chrome, 1400×900, device scale 2)**

Drive Chrome through CDP (remote debugging on a free port, a throwaway driver script in the scratchpad, never in the repo). Log in as `bohdan` (empty space; verify with `GET /files`), upload `Program.cs`, `photo.jpg`, `main.cpp`, `logo.png`, `notes.txt`, `archive.zip` through the hidden file input (`DOM.setFileInputFiles`), then re-upload `Program.cs` with different content.

1. `web-01-login.png` — `/login` with the «Сервер: http://localhost:3000» line.
2. `web-02-table.png` — all six files, all columns, ascending.
3. `web-03-sort-desc.png` — descending.
4. `web-04-filter.png` — «Лише .cpp, .png».
5. `web-05-columns.png` — five columns hidden.
6. `web-06-preview-cs.png` — `Program.cs` text preview.
7. `web-07-preview-jpg.png` — `photo.jpg` image preview.
8. `web-08-dragdrop.png` — synthetic `dragover` on the dropzone showing the drop hint.
9. `web-09-download.png` — after clicking «Скачати» (Chrome download bubble or the DevTools download event; if nothing is visible in headless mode, show the button pressed state and record the `Browser.downloadWillBegin` event in the task report).
10. `web-10-sync.png` — sync panel with a report line. Inject via `Runtime.evaluate` a `window.showDirectoryPicker` returning an in-memory directory handle (same shape as the Vitest fake) holding two files; click «Синхронізувати». The report line must show real numbers from the real API.
11. `web-11-tests.png` — Terminal window with `yarn test` (crop to the window; no absolute paths).
12. `web-12-prod.png` — `https://localhost/login` served by the production stack (bring it up with `docker compose -f docker/compose.prod.yml --env-file docker/.env.prod up -d --build --wait`, capture with `--ignore-certificate-errors`, then `down -v`).

Clean up: delete the uploaded files via the API, confirm `GET /files` is `[]`, stop the dev server.

- [ ] **Step 3: Write the report**

`docs/reports/stage3-web.md`, same front matter as `stage2-desktop.md` (title «Розробка клієнта для взаємодії з віддаленою папкою з файлами. Етап 3, варіант 4-6», `lang: uk`, author line, ToC). Sections:

1. Постановка задачі етапу 3 (веб-орієнтована версія; той самий сервер; вимоги R1–R9; бонус — публікація сервера).
2. Архітектура (monorepo, `apps/web` на Next.js App Router; повторне використання `packages/shared` і `packages/ui`; `DriveWorkspace` та `LoginForm` спільні для обох клієнтів — платформа передає лише `saveFile`, drag-out, панель синхронізації; REST-контракт без змін). Вставити рис. 05-class-clients.png і 15-component.png.
3. Технології (Next.js, React 19, Tailwind v4, shadcn/ui; REST через `ApiClient`; сесія в `localStorage`).
4. Веб-клієнт — підрозділи за функціями з відповідними знімками 1–9.
5. Синхронізація папки в браузері — File System Access API; чому браузер не може встановити mtime; журнал синхронізації (`SyncLedger`) як прийняте відхилення від правил §4.2; відсутність автоматичного спостереження; підтримка браузерів; знімок 10.
6. Тестування — таблиця тестів `apps/web` (`browserSync.test.ts`, 4 випадки) і `packages/shared` (`syncLedger.test.ts`, 6 випадків); підсумок 80 тестів; знімок 11.
7. Розгортання — dev-стек, production-стек (Caddy + web + api + postgres + minio, `compose.prod.yml`), CI; бонус «публікація сервера»: підготовлено; публічна адреса буде додана після розгортання на VM. Знімок 12.
8. Інструкція із запуску (dev і production).
9. Висновки.

Build: `tools/build-report.sh docs/reports/stage3-web.md`. Check with `pdfinfo`/`pdftotext` that the ToC and Ukrainian text render.

- [ ] **Step 4: Commit**

```bash
git add docs/reports/stage3-web.md docs/reports/stage3-web.docx docs/reports/stage3-web.pdf docs/reports/img/web-* README.md
git commit -m "docs: stage 3 report with web client screenshots"
```

---

### Task 9: Stage 4 comparison report

**Files:**
- Create: `docs/reports/stage4-comparison.md`, `docs/reports/stage4-comparison.docx`, `docs/reports/stage4-comparison.pdf`
- Modify: `README.md` (link)

**Interfaces:**
- Consumes: the finished code of Stages 2 and 3, both earlier reports.

- [ ] **Step 1: Gather the numbers**

From the repo root compute line counts with `git ls-files <dir> | grep -E '\.(ts|tsx|css)$' | grep -v '\.test\.\|\.spec\.' | xargs wc -l | tail -1` for `packages/shared/src`, `packages/ui/src`, `apps/api/src`, `apps/desktop/src`, `apps/web/src`, and test counts per workspace from `yarn test`. Record: lines per area; share of client code that is shared (`packages/ui` + `packages/shared` versus `apps/desktop/src` + `apps/web/src`); dependency counts from each `package.json`; artifact sizes (`apps/desktop/dist/MiniDrive-1.0.0-arm64.dmg`, `docker image ls minidrive-prod-web --format '{{.Size}}'` after a build, or the sizes noted in the Stage 3 task report).

- [ ] **Step 2: Write the report**

`docs/reports/stage4-comparison.md`, title «Розробка клієнта для взаємодії з віддаленою папкою з файлами. Етап 4, варіант 4-6», same front matter. Sections:

1. Мета порівняння.
2. Спільні елементи (сервер і REST-контракт, `packages/shared`, `packages/ui` з `DriveWorkspace`/`LoginForm`, однакові тести доменної логіки, той самий стек TypeScript/React/Tailwind).
3. Відмінності (таблиця): платформа запуску; зберігання сесії (safeStorage vs localStorage); доступ до файлової системи (Node fs vs File System Access API); синхронізація (mtime vs ledger; автоспостереження chokidar vs відсутнє); drag-and-drop (двонаправлений vs лише завантаження); скачування (нативний діалог vs завантаження браузера); пакування та розповсюдження (.dmg 100+ МБ vs Docker-образ і URL); оновлення (перевстановлення vs миттєве); підтримка браузерів/ОС; безпека (CSP, ізоляція процесів vs same-origin, CORS); продуктивність запуску; обсяг коду (таблиця рядків); залежності.
4. Переваги та недоліки кожної версії (списки).
5. Обґрунтування оптимальної технології — висновок: веб-версія як основна для системи типу 2 (нульове встановлення, розгортання одного стека, той самий код інтерфейсу), десктоп — там, де потрібні автоматична синхронізація та drag-out; завдяки `packages/ui` обидві версії коштують небагато разом.
6. Висновки.

Build with `tools/build-report.sh docs/reports/stage4-comparison.md`; check the PDF.

- [ ] **Step 3: Commit**

```bash
git add docs/reports/stage4-comparison.md docs/reports/stage4-comparison.docx docs/reports/stage4-comparison.pdf README.md
git commit -m "docs: stage 4 comparison of the desktop and web clients"
```

---

## Self-review

- Spec coverage: R1 (Task 3), R2–R7 (Task 4 via `DriveWorkspace`), R8 (Task 5, deviation recorded in Global Constraints), R9 upload drag-and-drop (Task 4, `UploadDropzone`), §3.4 pages/components/services (Tasks 2–5; `BrowserSyncEngine` and `SessionStore` named as in the spec), §6 cloud deployment prepared (Task 6; the actual publish waits for the user), §7 testing (Tasks 1, 5), report structure (Tasks 8, 9). Not done: drag-out from the browser (impossible with a Bearer-protected download URL) — explained in the Stage 4 report.
- Placeholder scan: none.
- Type consistency: `DirectoryHandleLike`/`FileHandleLike`/`LedgerStore` are defined in Task 5 and used only there; `LoginForm`/`DriveWorkspace` props match between Tasks 3–4 and their desktop wrappers; `configureApi`/`getApi` signatures are unchanged from the desktop original.

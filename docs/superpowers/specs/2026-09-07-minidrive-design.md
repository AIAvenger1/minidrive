# MiniDrive — design specification

Course project, "Informational technologies", 7th semester. System **type 2**: a client for a remote
folder with files (a lightweight Google Drive). Variant from student ID digits **46**:

| Digit | List | Value |
|---|---|---|
| 4 | TYPES (content shown on click) | `.cs` shown as text, `.jpg` shown as image |
| 6 | OPERATIONS | sort by **name** (ascending / descending); filter: **all files** or **only `.cpp`, `.png`** |

This document is the single source of truth for names used in the UML diagrams, the code and the
reports. Diagrams, code and reports must use the names below verbatim.

## 1. Scope and requirements

General requirements (apply to both the desktop and the web client):

- R1. Authorization on the remote server (register + log in); after log in the user is in a personal
  space ("cabinet", virtual disk).
- R2. View files in the space with attributes: **name, created at, modified at, uploaded by, modified by**
  (plus size and type as auxiliary columns).
- R3. Show or hide every column except **name**.
- R4. Sort by name ascending / descending (variant operation).
- R5. Filter: all files / only `.cpp` / only `.png` (variant operation; the two types are separate options).
- R6. Click a file to display its content: `.cs` as plain text, `.jpg` as image (variant type). Other
  types show attributes only with a "preview not available" note.
- R7. Upload files (a new file or a new version of an existing one), download files, delete files.
- R8. Synchronize a chosen local folder with the remote space (bind a folder first, then sync;
  desktop additionally can watch the folder and sync automatically).
- R9. Bonus: drag-and-drop for upload (both clients) and for download (desktop drag-out).

Non-goals: sharing between users, folders/sub-directories inside a space, in-app text editing,
version history, quotas.

## 2. Actors and use cases

Actor: **Користувач** (User) — a person with an account. An unauthenticated visitor can only
register or log in. Secondary actor for the deployment/sequence views: **MinIO** and **PostgreSQL**
are system-internal and are not actors in the use case diagram.

Top-level use cases (UA names are used verbatim in the diagrams):

| ID | Use case | Relationship |
|---|---|---|
| UC1 | Sign up | — (blue) |
| UC2 | Log in to the system | — (blue; note: all further interaction requires an authorized user) |
| UC3 | Work with the file storage | root; `include` UC2; `include` UC4 |
| UC4 | View the list of files and their attributes | included by UC3 (green) |
| UC5 | Sort by name | `extend` UC4; parameter leaves «Ascending», «Descending» |
| UC6 | Filter by type | `extend` UC4; parameter leaves «All files», «Only .cpp», «Only .png» |
| UC7 | Show / hide table columns | `extend` UC4; leaves «Creation date», «Modification date», «Uploaded by», «Edited by», «Size» |
| UC8 | View the file contents | `extend` UC4; leaves «.cs as text», «.jpg as image» |
| UC9 | Upload file(s) to the storage | `extend` UC3 (yellow); sub-cases UC9a «Select and upload», UC9b «Drag-and-drop» |
| UC10 | Update a file (new version) | `extend` UC3; note: updates «modification date» and «edited by» |
| UC11 | Download file(s) | `extend` UC3; sub-case UC11a «Drag out of the window» — desktop only |
| UC12 | Delete file(s) | `extend` UC3 |
| UC13 | Bind / change local folder | `extend` UC3 (purple) |
| UC14 | Synchronize with the local folder | `extend` UC3; precondition: a bound folder; sub-cases UC14a «Automatic tracking of folder changes» (desktop only), UC14b «Resolve version conflicts» (newest version wins) |
| UC15 | Log out from the system | — (blue) |

The VOPC diagram is drawn for the variant use cases **UC5 + UC6** ("Sort and filter the file list").

Preview rule (variant nuance): the variant's preview types (`.cs`, `.jpg`) and filter types
(`.cpp`, `.png`) differ because the two digits are independent. Preview is implemented generically:
any text-like file (`.cs`, `.cpp`, `.txt`, `.md`, `.json`, …) renders as text and any raster image
(`.jpg`, `.jpeg`, `.png`, `.gif`) renders as an image; `.cs` and `.jpg` are the mandatory cases named
in the report and tests.

## 3. Architecture

Monorepo (Yarn 4 workspaces, node-modules linker) with three applications and one shared package, all TypeScript:

```
inform_tech/
  apps/api/        NestJS 11 REST API (Prisma + PostgreSQL, MinIO via S3 SDK, JWT)
  apps/web/        Next.js web client
  apps/desktop/    Electron + React + Vite desktop client (local boot only)
  packages/shared/ Types, domain classes and pure functions shared by both clients
  docker/          docker-compose for api + postgres + minio (+ web + caddy in prod)
  docs/uml/        draw.io generator scripts (gen/), editable diagrams (drawio/), PNG+SVG (img/)
  docs/reports/    Stage reports (Markdown → DOCX/PDF)
```

Both clients talk to the same REST API over HTTPS/JSON. Sorting, filtering, column visibility,
preview selection and the sync plan are computed **client-side** with `packages/shared`, so they
are unit-testable without a server. The API stores metadata in PostgreSQL and bytes in MinIO.

### 3.1 Domain model (conceptual, used by the domain class diagram)

| Class | Attributes | Operations | Notes |
|---|---|---|---|
| `User` | `id`, `username`, `passwordHash`, `createdAt` | `register(username, password)`, `authenticate(username, password): Session` | one `Space` per user |
| `Session` | `token`, `user: User`, `expiresAt` | `isValid()`, `revoke()` | JWT on the client side |
| `Space` «virtual disk» | `id`, `owner: User`, `files: FileEntry[]` | `getFiles()`, `addFile(f)`, `removeFile(id)` | composition of `FileEntry` |
| `FileEntry` | `id`, `name`, `extension`, `size`, `createdAt`, `updatedAt`, `uploadedBy: User`, `modifiedBy: User`, `storageKey` | `isNewerThan(other)` | metadata row |
| `FileContent` | `storageKey`, `mimeType`, `bytes` | `getStream()` | object in MinIO |
| `FilePreview` «abstract» | `entry: FileEntry` | `canRender(ext)`, `render(): PreviewResult` | |
| `TextPreview` «.cs, text» | `encoding` | overrides | |
| `ImagePreview` «.jpg, image» | `width`, `height` | overrides | |
| `LocalFolder` | `path`, `boundAt` | `listFiles(): LocalFileInfo[]`, `isBound()` | |
| `SyncEngine` | `localFolder: LocalFolder`, `plan: SyncPlan` | `scan()`, `synchronize(): SyncReport`, `startWatching()`, `stopWatching()` | watching is desktop only |
| `SyncPlan` | `uploads`, `downloads`, `skipped: SyncAction[]` | — | produced by `computeSyncPlan` |
| `SyncAction` | `kind: upload/download/skip`, `name`, `reason` | — | |
| `SyncReport` | `uploaded`, `downloaded`, `skipped`, `failed: number`, `errors: string[]` | — | |

### 3.2 Server — `apps/api` (NestJS)

Modules and classes (names are final):

| Module | Classes | Responsibility |
|---|---|---|
| `AuthModule` | `AuthController`, `AuthService`, `JwtStrategy`, `JwtAuthGuard` | register, login, issue/verify JWT |
| `UsersModule` | `UsersService` | find/create users, hash passwords (bcrypt) |
| `FilesModule` | `FilesController`, `FilesService` | list/upload/download/delete, metadata |
| `StorageModule` | `StorageService` | put/get/delete objects in MinIO (S3 API) |
| `PrismaModule` | `PrismaService` | database access |

Entities (Prisma models):

```
User      { id: string (uuid), username: string (unique), passwordHash: string, createdAt: DateTime }
FileEntry { id: string (uuid), ownerId: string → User, name: string, extension: string,
            size: number, storageKey: string, createdAt: DateTime, updatedAt: DateTime,
            uploadedById: string → User, modifiedById: string → User }
```

Unique constraint: (`ownerId`, `name`). `storageKey` = `users/{ownerId}/{fileEntry.id}` in bucket
`minidrive`. Uploading a file whose name already exists in the space **overwrites** it (UC10): same
`FileEntry` row and storage key, new bytes, `updatedAt` = now, `modifiedById` = current user.

DTOs: `RegisterDto {username, password}`, `LoginDto {username, password}`,
`AuthResponseDto {accessToken, user: UserDto}`, `UserDto {id, username}`,
`FileDto {id, name, extension, size, createdAt, updatedAt, uploadedBy: string, modifiedBy: string}`.

REST API (all `/files` routes require `Authorization: Bearer <jwt>`):

| Method | Path | Body / query | Returns |
|---|---|---|---|
| POST | `/auth/register` | `RegisterDto` | `AuthResponseDto` |
| POST | `/auth/login` | `LoginDto` | `AuthResponseDto` |
| GET | `/auth/me` | — | `UserDto` |
| GET | `/files` | — | `FileDto[]` (whole space, unsorted) |
| POST | `/files` | multipart, field `file` | `FileDto` (created or overwritten) |
| GET | `/files/:id/content` | — | bytes, `Content-Type`, `Content-Disposition` |
| DELETE | `/files/:id` | — | 204 |

Errors: 401 unauthorized, 404 file not in caller's space, 409 username taken, 413 file too large
(limit 50 MB), 400 validation.

### 3.3 Shared package — `packages/shared`

Types: `FileDto`, `SortOrder = 'asc' | 'desc'`, `FileFilter = 'all' | 'cpp' | 'png'`,
`ColumnKey = 'name' | 'size' | 'extension' | 'createdAt' | 'updatedAt' | 'uploadedBy' | 'modifiedBy'`,
`ColumnVisibility = Record<ColumnKey, boolean>` (name is always `true`),
`PreviewKind = 'text' | 'image' | 'none'`, `LocalFileInfo {name, size, mtime}`,
`SyncAction`, `SyncPlan`, `SyncReport` (see §3.1).

Classes: `FilePreview` (abstract), `TextPreview`, `ImagePreview`, factory `createPreview(entry)`.

Pure functions (each unit-tested):

| Function | Behaviour |
|---|---|
| `sortByName(files, order)` | stable, locale-aware (`localeCompare` with `numeric: true`), case-insensitive; `asc` / `desc` |
| `filterByType(files, filter)` | `'all'` returns a copy; `'cpp'` keeps `.cpp` files, `'png'` keeps `.png` files (case-insensitive); the two variant types are offered as separate options (user decision, 2026-09-08) |
| `previewKindOf(name)` | text-like extensions (`cs`, `cpp`, `c`, `h`, `txt`, `md`, `json`, `js`, `ts`, `py`, `java`, `kt`, `xml`, `html`, `css`) → `'text'`; raster images (`jpg`, `jpeg`, `png`, `gif`, `bmp`, `webp`) → `'image'`; else `'none'` |
| `toggleColumn(visibility, key)` | flips a column; `name` cannot be hidden |
| `computeSyncPlan(local, remote)` | see §4.2 |

### 3.4 Web client — `apps/web` (Next.js, App Router)

Pages: `/login` (login + register form), `/drive` (cabinet).
Components: `FileTable`, `ColumnToggle`, `SortControl`, `FilterControl`, `PreviewPanel`,
`UploadDropzone`, `SyncPanel`. Services: `ApiClient` (fetch wrapper with JWT), `SessionStore`
(token in `localStorage`), `BrowserSyncEngine` (File System Access API, Chrome/Edge; other browsers
see "sync unavailable"; no automatic watching).

### 3.5 Desktop client — `apps/desktop` (Electron + React + Vite)

Processes: **Main** (`MainWindow`, `IpcHandlers`, `LocalFolderScanner`, `SyncEngine`,
`FolderWatcher`, `DragOutHandler`), **Preload** (`PreloadBridge`, exposes `window.minidrive`),
**Renderer** (same React components as web: `FileTable`, `ColumnToggle`, `SortControl`,
`FilterControl`, `PreviewPanel`, `UploadDropzone`, `SyncPanel`, plus `ApiClient`, `SessionStore`
storing the token in Electron `safeStorage`).
Drag-and-drop: drop files on the window → upload; drag a row out of the window → native drag-out
(`webContents.startDrag`) that downloads the file to the drop target.

## 4. Key behaviours

### 4.1 Preview (UC8)

Clicking a row calls `createPreview(entry)` → `previewKindOf(name)`. `TextPreview` → GET
`/files/:id/content`, show in a monospace read-only panel. `ImagePreview` → same endpoint as an
`<img>` source (blob URL). `'none'` → attributes only.

### 4.2 Sync (UC14) — `computeSyncPlan(local, remote)`

Inputs: local entries `{name, size, mtime}` from the bound folder (top level only, files only) and
remote `FileDto[]`. Rules per file name (case-sensitive):

1. only local → **upload**;
2. only remote → **download**;
3. both, same size and |mtime − updatedAt| ≤ 2 s → **skip**;
4. both, otherwise (version conflict, UC14b) → **newest wins**: local mtime newer → upload, else download.

Deletions never propagate (a missing file on one side is copied, never removed). The client then
executes the plan: uploads via POST `/files`, downloads via GET `/files/:id/content`, sets the local
file mtime to the remote `updatedAt` after download, and shows a `SyncReport`. On desktop,
`FolderWatcher` (UC14a) debounces file-system events and re-runs the sync.

### 4.3 Authentication

JWT (HS256, 24 h) in the `Authorization` header. Passwords hashed with bcrypt. Clients keep the
token in `SessionStore`; a 401 clears it and returns to the login screen.

## 5. State machines

**Client session**: `LoggedOut` → (login ok) → `LoggedIn` with sub-states `Browsing` ⇄ `Previewing`,
`Browsing` → `Uploading` → `Browsing`, `Browsing` → `Syncing` → `Browsing`; any 401 or logout →
`LoggedOut`.

**Sync session**: `Idle` → `Scanning` (read local folder, GET /files) → `Planning`
(`computeSyncPlan`) → `Transferring` (uploads/downloads) → `Completed` | `Failed` → `Idle`;
`Watching` (desktop) loops back into `Scanning` on a file-system event.

## 6. Deployment

- **Local (Stage 2)**: developer macOS runs `docker compose up` (containers `api`, `postgres`,
  `minio`) and the Electron app (`yarn workspace @minidrive/desktop dev`). Web dev server optional.
- **Cloud (Stage 3 bonus)**: one Linux VM (Hetzner Cloud CX23; domain from the GitHub Student Developer Pack)
  runs Docker Compose with `caddy` (TLS reverse proxy), `api`, `web` (Next.js standalone),
  `postgres`, `minio`. Public URL for the web client and the API; the desktop client points at the
  same API URL.

## 7. Testing

- `packages/shared`: Vitest unit tests for `sortByName` (variant operation), `filterByType`
  (variant operation), `previewKindOf`, `toggleColumn`, `computeSyncPlan`.
- `apps/api`: Jest unit tests for `FilesService` (overwrite semantics) and `AuthService`, plus one
  e2e test with supertest against a test database.
- `apps/desktop`: Vitest tests for `SyncEngine` with a temp folder and a mocked `ApiClient`.

## 8. Stage 1 deliverables (UML)

Generator scripts in `docs/uml/gen`, editable files in `docs/uml/drawio`, PNG + SVG in `docs/uml/img`:

| # | File | Diagram |
|---|---|---|
| 01 | `01-use-case.drawio` | Use case diagram (all UCs of §2, with notes) |
| 02 | `02-class-domain.drawio` | Class diagram: conceptual domain model (§3.1) with multiplicities |
| 03 | `03-class-vopc-sort-filter.drawio` | **VOPC** for UC5+UC6 (boundary / control / entity) |
| 04 | `04-class-server.drawio` | Class diagram: API modules, controllers, services, entities, DTOs |
| 05 | `05-class-clients.drawio` | Class diagram: shared package, web and desktop clients |
| 06 | `06-activity-sync.drawio` | Activity diagram: UC14 sync with swimlanes |
| 07 | `07-activity-upload.drawio` | Activity diagram: UC9/UC10 upload incl. drag-and-drop and overwrite |
| 08 | `08-sequence-login.drawio` | Sequence diagram: UC1/UC2 |
| 09 | `09-sequence-upload-preview.drawio` | Sequence diagram: UC9 then UC8 |
| 10 | `10-sequence-sync.drawio` | Sequence diagram: UC14 |
| 11 | `11-communication-sort-filter.drawio` | Communication diagram: UC5+UC6 |
| 12 | `12-state-session.drawio` | State diagram: client session (§5) |
| 13 | `13-state-file.drawio` | State diagram: file lifecycle during sync (LocalOnly / RemoteOnly / Synced / ModifiedLocally / ModifiedRemotely / Conflict / Deleted) |
| 14 | `14-state-sync.drawio` | State diagram: sync session (§5) |
| 15 | `15-component.drawio` | Component diagram with interfaces |
| 16 | `16-deployment.drawio` | Deployment diagram: local and cloud |

Language rule: **all diagram text is English** (use case names, states, actions, classes, notes);
the report text is Ukrainian. English use case names map directly onto class and method names.
Level of detail: every use case ellipse that appears in §2 (including sub-cases) is drawn; every
domain class in §3.1 shows its attributes and operations.

Tooling: diagrams are generated as native, editable draw.io files by Python scripts in
`docs/uml/gen/NN_name.py` using `tools/drawio_gen/drawio.py`; outputs are `docs/uml/drawio/NN-name.drawio`
plus `docs/uml/img/NN-name.png` (preview, 2x) and `docs/uml/img/NN-name.svg` (for the Word report).
Once the owner hand-edits a `.drawio`, that file becomes the source of truth and later changes are
applied as patches to it.

Use case diagram style: **cascade** — the actor connects to a few root use cases (log in, log out,
work with the file storage); everything else hangs as a tree through `include` / `extend`; parameter
leaves (ascending/descending, all/only .cpp .png, column names, .cs/.jpg) hang on plain solid lines.
No system-boundary package box. Colour groups carried across all diagrams: **blue** = access
(register/login/logout/session), **green** = file list (view, sort, filter, columns, preview),
**yellow** = file operations (upload, update, download, delete), **purple** = synchronization,
**grey** = infrastructure (storage, database, hosting).

## 9. Report structure (Stage 1, Ukrainian)

Title: «Розробка клієнта для взаємодії з віддаленою папкою з файлами. Етап 1, варіант 4-6».
Sections: титульна сторінка → зміст → постановка задачі (умова, варіант, вимоги) → аналіз вимог
(actors, use cases, functional / non-functional requirements, the variant nuance) → високорівневе
проєктування (architecture, components, deployment) → деталізоване проєктування (class diagrams,
VOPC, activity, interaction, state diagrams) → кожна діаграма з абзацом «Пояснення» → висновок.
Images: SVG for Word (scales without pixelation), PNG for the PDF/Markdown.

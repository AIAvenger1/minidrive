---
title: "Розробка клієнта для взаємодії з віддаленою папкою з файлами. Етап 2, варіант 4-6"
subtitle: "Десктоп-версія (Electron) та сервер (NestJS)"
author:
  - "Виконав: студент групи МІ-41 Петров Богдан"
  - "Перевірив: \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_"
date: "Київський національний університет імені Тараса Шевченка  \\newline Дисципліна «Інформаційні технології»  \\newline Київ — 2026"
lang: uk
toc-title: "Зміст"
---

# Постановка задачі

Завдання етапу 2 — реалізувати десктоп-клієнт (Electron) і серверну частину (NestJS) системи MiniDrive для варіанта 4-6, спроєктованої на етапі 1 (звіт `stage1-uml.md`): реєстрацію та вхід, перегляд файлів власного простору з атрибутами, сортування за назвою, фільтр «лише `.cpp`, `.png`», перегляд вмісту `.cs` як тексту та `.jpg` як зображення, завантаження/вивантаження/видалення файлів, синхронізацію локальної папки з віддаленим простором, а також обидва бонуси — drag-and-drop при за- і вивантаженні. Постановку задачі, аналіз вимог і UML-специфікацію детально описано на етапі 1; цей звіт фіксує їх реалізацію, unit-тести та результати запуску.

# Архітектура реалізації

Проєкт — монорепозиторій на Yarn 4 workspaces (`packageManager: yarn@4.9.1`, `nodeLinker: node-modules`, без PnP):

- `packages/shared` — спільна TypeScript-логіка без залежностей від Electron, DOM чи Node: типи (`FileDto`, `UserDto`, `AuthResponseDto` тощо), `ApiClient` (обгортка над REST), чисті функції варіанта `sortByName`/`filterByType`, `previewKindOf`/`createPreview`, `toggleColumn`, `DriveViewModel` (фасад стану екрана) та `computeSyncPlan` (правила синхронізації). Пакет збирається у dual ESM/CJS і використовується і десктоп-, і майбутнім веб-клієнтом.
- `packages/ui` — презентаційні компоненти на React + shadcn/Tailwind (`FileTable`, `SortControl`, `FilterControl`, `ColumnToggle`, `PreviewPanel`, `UploadDropzone`), незалежні від платформи: усе платформозалежне передається пропсами.
- `apps/api` — сервер NestJS: модулі `auth`, `users`, `files`, `storage`, `prisma`.
- `apps/desktop` — Electron-застосунок (electron-vite): процеси `main` (вікно, IPC, `SyncEngine`, `FolderWatcher`, `LocalFolderScanner`, `DragOutHandler`), `preload` (`PreloadBridge`, тобто `window.minidrive`) і `renderer` (React-екрани `LoginScreen`/`DriveScreen` на компонентах `packages/ui`).

Відповідність діаграмам етапу 1: компонентна структура (рис. 1 етапу 1, `docs/uml/img/15-component.png`) один в один відповідає поділу на `packages/shared`, `apps/api` і три процеси `apps/desktop`; діаграма класів сервера (рис. 6, `docs/uml/img/04-class-server.png`) — контролерам/сервісам NestJS нижче; діаграма класів клієнтів (рис. 7, `docs/uml/img/05-class-clients.png`) — файлам `packages/shared/src/*.ts` і компонентам `packages/ui`.

![Діаграма компонентів (етап 1)](../uml/img/15-component.png){width=16cm}

![Діаграма класів сервера (етап 1)](../uml/img/04-class-server.png){width=16cm}

![Діаграма класів спільного пакета і клієнтів (етап 1)](../uml/img/05-class-clients.png){width=16cm}

# Сервер

REST API (NestJS, префікс без версії, порт 3000):

| Метод і шлях | Призначення | Успіх | Помилки |
|---|---|---|---|
| `POST /auth/register` | реєстрація нового користувача | 201, `AuthResponseDto` | 409 — ім'я зайняте, 400 — валідація |
| `POST /auth/login` | вхід за логіном/паролем | 200, `AuthResponseDto` | 401 — невірний пароль |
| `GET /auth/me` | поточний користувач за токеном | 200, `UserDto` | 401 |
| `GET /files` | список файлів власного простору | 200, `FileDto[]` | 401 |
| `POST /files` | завантаження файлу (multipart, поле `file`) | 201, `FileDto` | 401, 413 — понад 50 МБ, 400 |
| `GET /files/:id/content` | вміст файлу (стрім) | 200, потік байтів | 401, 404 — файл не в просторі викликача |
| `DELETE /files/:id` | видалення файлу | 204 | 401, 404 |

Автентифікація — JWT HS256 з часом життя 24 год у заголовку `Authorization: Bearer <token>`; паролі хешуються bcrypt (10 раундів). Дані зберігаються в PostgreSQL через Prisma; модель `FileEntry` містить `ownerId`, `name`, `extension`, `size`, `storageKey`, `createdAt`, `updatedAt`, `uploadedById`, `modifiedById` і унікальний індекс `(ownerId, name)`; модель `User` — `id`, `username` (унікальний), `passwordHash`.

Вміст файлів зберігається в MinIO (S3-сумісне сховище), бакет `minidrive`, ключ об'єкта — `users/{ownerId}/{fileEntry.id}`. `StorageService` інкапсулює `putObject`/`getObject`/`deleteObject` і за потреби створює бакет при старті (`onModuleInit`).

Правило перезапису: якщо завантажене ім'я вже існує у просторі того самого власника, `FilesService.upsert` не створює новий рядок, а лишає той самий `FileEntry.id` і `storageKey`, замінює байти в MinIO, ставить `updatedAt = now()` і `modifiedById = caller`. Це перевірено тестом `FilesService.upsert`: «overwrites an existing name: same id and key, new bytes, modifiedBy = caller» (`apps/api/src/files/files.service.spec.ts`).

Стек піднімається `docker compose` (`docker/compose.yml`): сервіси `postgres`, `minio` та `api` (образ будується з `docker/api.Dockerfile`), усі з healthcheck. У робочому стані:

![Термінал: `docker compose ps`, усі три сервіси healthy](img/12-docker.png){width=15cm}

Специфікація REST-інтерфейсу автоматично публікується через `@nestjs/swagger` на `/docs`:

![Swagger UI (`http://localhost:3000/docs`)](img/10-swagger.png){width=13cm}

Наскрізна перевірка проти живого стеку — скрипт `tools/api-smoke.sh` (реєстрація/вхід відсутні, бо користувачі вже засіяні `db:seed`; сценарій: вхід → завантаження → список → вивантаження → видалення), який використано замість e2e-тесту supertest (узгоджене відхилення від §7 специфікації).

# Десктоп-клієнт

Нижче — кожна функція десктоп-клієнта зі скриншотом. Знімки зроблено в чистому стані: вхід під `bohdan`, завантаження `Program.cs`, `photo.jpg`, `main.cpp`, `logo.png`, `notes.txt`, `archive.zip`, повторне завантаження `Program.cs` (щоб «Змінено» відрізнялося від «Створено»); після зйомки тестові файли видалено з сервера.

## Вхід і адреса сервера

Екран входу (`LoginScreen`) має поле «Адреса сервера» (за замовчуванням `http://localhost:3000`, зберігається в `electron-store` через `SessionStore`), ім'я користувача й пароль; той самий екран перемикається в режим реєстрації. Змінюючи адресу сервера, клієнт можна спрямувати на інший (наприклад, опублікований в інтернеті) інстанс API без перезбирання застосунку.

![Екран входу з полем адреси сервера](img/01-login.png){width=11cm}

## Таблиця файлів і атрибути

`FileTable` показує «Назва», «Тип», «Розмір», «Створено», «Змінено», «Завантажив», «Редагував». Оскільки простори персональні і функція «поділитися» поза межами проєкту (sharing out of scope), у власному просторі «Завантажив» і «Редагував» завжди показують того самого користувача — це очікувана поведінка, а не помилка; стовпці все одно виведено обидва, щоб інтерфейс був готовий до можливого розширення. Значення розходяться, коли файл із тим самим іменем вивантажується повторно: «Редагував» лишається як є (той самий викликач у персональному просторі), а «Змінено» оновлюється — новий файл `Program.cs` це демонструє (розділ «Синхронізація» нижче: «Змінено» 22:48:11 проти «Створено» 22:42:51).

![Таблиця з усіма стовпцями, сортування за зростанням](img/02-table.png){width=15cm}

## Сортування за назвою (операція варіанта)

`SortControl` перемикає порядок сортування за клацанням на «Назва»; сортування стабільне, регістронезалежне, з `localeCompare(..., { numeric: true })` (`sortByName`, `packages/shared/src/fileList.ts`).

![Сортування за спаданням](img/03-sort-desc.png){width=15cm}

## Фільтр за типом (операція варіанта)

`FilterControl` — перемикач «Усі файли» / «Лише `.cpp`, `.png`» (`filterByType`, регістронезалежний за розширенням).

![Фільтр «Лише .cpp, .png»: залишились logo.png і main.cpp](img/04-filter.png){width=15cm}

## Показ/приховування стовпців

`ColumnToggle` — прапорці для всіх стовпців, крім «Назва», яку приховати неможливо (перевірено тестом `toggleColumn`: «never hides the name column»).

![Кілька стовпців приховано, «Назва» лишається видимою](img/05-columns.png){width=15cm}

## Перегляд вмісту: `.cs` як текст, `.jpg` як зображення (тип варіанта)

`PreviewPanel` викликає `createPreview`/`previewKindOf` із `packages/shared`: текстові розширення (зокрема `.cs`) рендеряться як текст, растрові зображення (зокрема `.jpg`) — як `<img>`.

![Перегляд `.cs` як тексту](img/06-preview-cs.png){width=15cm}

![Перегляд `.jpg` як зображення](img/07-preview-jpg.png){width=15cm}

## Завантаження: кнопка та drag-and-drop (бонус)

`UploadDropzone` поєднує кнопку «Завантажити файли» (прихований `<input type="file" multiple>`) і зону перетягування: `onDragOver` показує підказку «Відпустіть, щоб завантажити», `onDrop` передає файли в той самий обробник завантаження, що й кнопка.

![Підказка під час перетягування файлів у вікно](img/08-dragdrop.png){width=15cm}

## Вивантаження і перетягування назовні (бонус)

Кнопка «Вивантажити» зберігає вміст обраного файлу через нативний діалог збереження (`window.minidrive.file.saveAs`, головний процес, `dialog.showSaveDialog`). Перетягування рядка таблиці назовні вікна обробляє `DragOutHandler` у головному процесі (`window.minidrive.file.dragOut`) — Electron записує тимчасовий файл і починає системний drag, тож файл можна відпустити у Finder або іншому застосунку.

## Видалення

Кнопка «Видалити» відкриває діалог підтвердження (`Dialog`/`DialogFooter` з `packages/ui`) і після підтвердження викликає `DELETE /files/:id`.

## Прив'язка папки

Панель синхронізації (`SyncPanel`) дозволяє прив'язати локальну папку через нативний діалог вибору директорії (`window.minidrive.folder.pick`, `dialog.showOpenDialog` з `openDirectory`); шлях зберігається в налаштуваннях і показується поруч із кнопкою «Змінити».

## Синхронізація та автоматичне відстеження

Кнопка «Синхронізувати» викликає `SyncEngine.synchronize()`: `LocalFolderScanner.scan()` читає локальну папку, `ApiClient.listFiles()` — віддалений список, `computeSyncPlan` будує план дій, які виконуються послідовно; результат — `SyncReport` (`uploaded`, `downloaded`, `skipped`, `failed`, `errors`), показаний у панелі. Прапорець «Автоматично відстежувати зміни» вмикає `FolderWatcher.startWatching()` (chokidar, дебаунс 2 с): кожна зміна у прив'язаній папці запускає нову синхронізацію без участі користувача; `stopWatching()` вимикає стеження.

![Панель синхронізації з рядком звіту: довантажено 6 файлів із сервера](img/09-sync.png){width=15cm}

## Правила синхронізації

Реалізовано в `computeSyncPlan` (`packages/shared/src/sync.ts`) і покрито тестами `sync.test.ts` та `syncEngine.test.ts`: файл лише локально → вивантажується; файл лише віддалено → довантажується; за наявності з обох боків з однаковим розміром і `|mtime − updatedAt| ≤ 2000` мс — пропускається; інакше перемагає новіша версія (за `mtime`/`updatedAt`); видалення ніколи не поширюються в інший бік (видалення локально відновлює файл з сервера і навпаки); після довантаження локальний `mtime` виставляється рівним `updatedAt` сервера, щоб наступна синхронізація не вважала файл зміненим.

# Unit-тестування

| Файл тестів | Що перевіряє | К-сть |
|---|---|---|
| `packages/shared/src/fileList.test.ts` | `sortByName` (зростання/спадання, стабільність, регістронезалежність — **операція варіанта**), `filterByType` (усі файли / лише `.cpp`,`.png` — **операція варіанта**), `extensionOf` | 6 |
| `packages/shared/src/preview.test.ts` | `previewKindOf` для типів варіанта `.cs`→текст, `.jpg`→зображення, узагальнено для інших текстових/растрових, `'none'` для інших; `createPreview` | 6 |
| `packages/shared/src/columns.test.ts` | `toggleColumn`, незнімний стовпець «Назва», `hideAllButName` | 3 |
| `packages/shared/src/driveViewModel.test.ts` | `DriveViewModel`: застосування сортування й фільтра варіанта до `visibleFiles`, неможливість приховати «Назва» | 2 |
| `packages/shared/src/apiClient.test.ts` | `ApiClient`: bearer-токен, `ApiError` зі статусом, multipart з полем `file` | 3 |
| `packages/shared/src/sync.test.ts` | `computeSyncPlan`: лише локально/лише віддалено, пропуск у межах похибки годинника, перемога новішої версії, різниця розміру як зміна | 6 |
| `apps/api/src/auth/auth.service.spec.ts` | реєстрація, 409 на зайняте ім'я, 401 на невірний пароль, вхід | 4 |
| `apps/api/src/files/files.service.spec.ts` | `FilesService.upsert` (створення, **перезапис з тим самим id/key**), валідація імені, чужий простір (404), відкат рядка при помилці сховища, порядок видалення | 8 |
| `apps/api/src/storage/storage.service.spec.ts` | `StorageService.putObject/getObject/deleteObject`, створення бакета при відсутності | 3 |
| `apps/api/src/users/users.service.spec.ts` | bcrypt-хеш пароля, пошук за іменем | 2 |
| `apps/desktop/src/main/sync/syncEngine.test.ts` | `SyncEngine.scan/synchronize`: за- і вивантаження, встановлення mtime, пропуск ідентичних, підрахунок помилок без переривання, захист від виходу за межі каталогу | 4 |

Разом: **shared — 26**, **api — 17**, **desktop — 4**, усього 47 тестів, усі проходять (`yarn test` з кореня):

![Термінал з результатом `yarn test`: 4 test suites api / 1 test file desktop / 6 test files shared, усі passed](img/11-tests.png){width=15cm}

# Інструкція із запуску

```bash
corepack enable
yarn install
cp docker/.env.example docker/.env
yarn stack:up
yarn workspace @minidrive/api db:seed
yarn workspace @minidrive/desktop dev
```

`yarn stack:up` піднімає `postgres`, `minio` та `api` в Docker (`docker compose -f docker/compose.yml up -d --build --wait`) і чекає на healthcheck усіх трьох сервісів; `yarn workspace @minidrive/api db:seed` створює тестових користувачів (`bohdan`, `olena`, `taras`, пароль `secret123`). `yarn workspace @minidrive/desktop dev` запускає Electron-клієнт у режимі розробки (electron-vite); `yarn workspace @minidrive/desktop build:mac` (або `build:win`/`build:linux`) збирає розповсюджуваний застосунок.

Змінні середовища сервера (`docker/.env`, копія з `docker/.env.example`, у git не потрапляє): `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`, `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`, `JWT_SECRET`, `API_PORT`, `CORS_ORIGINS`.

Щоб підключити десктоп-клієнт до віддаленого (не локального) сервера, достатньо на екрані входу вказати в полі «Адреса сервера» URL опублікованого API (наприклад, `https://minidrive.example.com`) замість `http://localhost:3000` — значення зберігається в `electron-store` й використовується для всіх наступних запитів `ApiClient`, перезбирання застосунку не потрібне.

# Пакування

`yarn workspace @minidrive/desktop build:mac` (electron-builder) успішно зібрав непідписаний застосунок: `apps/desktop/dist/mac-arm64/desktop.app` (~615 МБ, arm64) і архів `apps/desktop/dist/desktop-1.0.0-arm64-mac.zip`. Підписання коду вимкнено додаванням `identity: null` у розділ `mac` `apps/desktop/electron-builder.yml` (сертифікатів розробника в системі немає — очікувано для навчального середовища). Фінальний крок побудови `.dmg` завершився помилкою electron-builder: артефакт `dmg.artifactName` за замовчуванням підставляє повне ім'я пакета `@minidrive/desktop` (зі слешем зі скоупу) у шлях файлу, отримуючи неіснуючий каталог `dist/@minidrive/…dmg` — це відома вада шаблону electron-vite з workspace-скоупованими іменами пакетів, не пов'язана з підписанням; `.app` і `.zip` при цьому побудовані коректно й запускаються.

# Висновки

На етапі 2 реалізовано REST-сервер (NestJS, PostgreSQL, MinIO) і десктоп-клієнт (Electron) системи MiniDrive за специфікацією етапу 1: усі функціональні вимоги типу 2, обидві операції варіанта (сортування за назвою, фільтр `.cpp`/`.png`), обидва типи перегляду варіанта (`.cs`, `.jpg`) і обидва бонуси (drag-and-drop за/вивантаження) реалізовано й перевірено вручну через 12 знімків екрана. Поведінку ключових функцій — сортування, фільтрації, перегляду, атрибутів перезапису та правил синхронізації — покрито 47 unit-тестами (shared 26, api 17, desktop 4), усі проходять. Наскрізну працездатність стеку підтверджує `tools/api-smoke.sh` проти запущеного `docker compose`. Пакування в розповсюджуваний `.app`/`.zip` для macOS пройшло успішно; крок побудови `.dmg` має відому й задокументовану вище проблему шаблону, що не впливає на роботу застосунку. Наступний етап (3) — веб-орієнтована версія клієнта на тому самому пакеті `packages/shared`.

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
yarn workspace @minidrive/api db:seed
yarn workspace @minidrive/desktop dev
```

`yarn stack:up` піднімає сервер у Docker (PostgreSQL, MinIO, API) і чекає, поки всі сервіси стануть healthy; `db:seed` створює тестових користувачів (`bohdan`, `olena`, `taras`, пароль `secret123`). Щоб підключити десктоп-клієнт до іншого (наприклад, віддаленого) сервера, на екрані входу достатньо змінити поле «Адреса сервера» — перезбирання не потрібне.

Тести: `yarn test` з кореня. Пакування десктоп-клієнта: `yarn workspace @minidrive/desktop build:mac` (або `build:win`/`build:linux`) — результат: `apps/desktop/dist/MiniDrive-1.0.0-arm64.dmg` і `apps/desktop/dist/MiniDrive-1.0.0-arm64.zip`. Детальніше — у звітах `docs/reports/stage1-uml.md` та `docs/reports/stage2-desktop.md`.

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

Веб-клієнт: `cp apps/web/.env.example apps/web/.env.local`, потім `yarn web:dev` і відкрити `http://localhost:3001`.

Тести: `yarn test` з кореня. Пакування десктоп-клієнта: `yarn workspace @minidrive/desktop build:mac` (або `build:win`/`build:linux`) — результат: `apps/desktop/dist/MiniDrive-1.0.0-arm64.dmg` і `apps/desktop/dist/MiniDrive-1.0.0-arm64.zip`. Детальніше — у звітах `docs/reports/stage1-uml.md`, `docs/reports/stage2-desktop.md` та `docs/reports/stage3-web.md`.

## Розгортання (production)

```bash
cp docker/.env.prod.example docker/.env.prod
```

У `docker/.env.prod` встановити `DOMAIN` — публічне ім'я хоста, яке вказує на VM, і задати паролі для PostgreSQL, MinIO та `JWT_SECRET`. На VM мають бути відкриті порти 80 і 443. Далі:

```bash
docker compose -f docker/compose.prod.yml --env-file docker/.env.prod up -d --build
```

Веб-клієнт піднімається на `https://DOMAIN`, API — на `https://DOMAIN/api` (Caddy сам видає TLS-сертифікат через Let's Encrypt). Десктоп-клієнт підключати до `https://DOMAIN/api` як адресу сервера. Swagger (`/api/docs`) у production вимкнено (`SWAGGER_ENABLED=false`).

CI (`.github/workflows/ci.yml`) при кожному push і pull request збирає проєкт (`yarn build`) і запускає тести (`yarn test`).

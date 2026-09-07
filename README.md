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

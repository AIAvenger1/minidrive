FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json yarn.lock .yarnrc.yml tsconfig.base.json ./
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

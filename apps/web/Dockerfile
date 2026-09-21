# TanStack Start front-end. Built with pnpm in the workspace, served by the nitro node server.
FROM node:22-alpine AS build

RUN corepack enable && corepack prepare pnpm@11.1.0 --activate
WORKDIR /repo

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --filter web

COPY apps/api/openapi.json apps/api/openapi.json
COPY apps/web apps/web
RUN pnpm --filter web generate:client && pnpm --filter web build

FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    API_URL=http://api:8000

WORKDIR /app
COPY --from=build /repo/apps/web/.output ./.output

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]

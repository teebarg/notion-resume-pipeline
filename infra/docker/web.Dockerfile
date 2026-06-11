FROM node:20-alpine

RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* bun.lockb* ./
# Copy workspace package config
COPY apps/web/package.json ./apps/web/

# Install dependencies based on lockfile at root
RUN \
  if [ -f "package-lock.json" ]; then npm ci; \
  elif [ -f "yarn.lock" ]; then yarn --frozen-lockfile; \
  elif [ -f "pnpm-lock.yaml" ]; then corepack enable pnpm && pnpm i; \
  elif [ -f "bun.lockb" ]; then corepack enable bun && bun install; \
  else npm install; \
  fi

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

WORKDIR /app/apps/web

CMD ["npm", "run", "dev"]

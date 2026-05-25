FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN corepack enable

COPY package.json pnpm-lock.yaml ./

RUN pnpm install

EXPOSE 3000

# Don't copy source — mount it as a volume instead
CMD ["pnpm", "dev"]
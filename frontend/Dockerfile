FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY next.config.mjs ./
RUN npm run build

# standalone output bundles the server into .next/standalone.
# Copy static assets into the standalone tree so they are served correctly.
RUN cp -r .next/static .next/standalone/.next/static 2>/dev/null || true

# Copy public directory if it exists
COPY public* ./public/
RUN cp -r public .next/standalone/public 2>/dev/null || true

EXPOSE 3000
# Next.js standalone server reads PORT from the environment automatically.
CMD ["sh", "-c", "node .next/standalone/server.js"]

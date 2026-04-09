FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY next.config.mjs ./
RUN npm run build

# Copy public directory if it exists
COPY public* ./public/

EXPOSE 3000
CMD ["sh", "-c", "npm run start -- -p ${PORT:-3000}"]

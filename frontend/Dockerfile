FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY next.config.mjs ./

# Copy public directory if it exists
COPY public* ./public/

ENV API_PROXY_TARGET=https://helper-backend-production.up.railway.app

RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]

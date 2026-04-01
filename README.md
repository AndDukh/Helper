# Helper

Helper is a Telegram Mini App + Bot for meeting capture, protocol generation, task tracking, and AI-assisted execution.

## Repository Structure

- `frontend/` - Telegram Mini App (UI).
- `backend/` - API service (meetings, protocols, tasks, auth).
- `worker/` - background jobs (STT, protocol generation, reminders, AI execution).
- `telegram-bot/` - long-polling bot that opens the Mini App via WebApp button.
- `infra/` - infra configs and local ops notes.
- `docs/` - PRD and implementation planning docs.

## Telegram Mini App: вывести в Telegram и тест на компьютере

Mini App в Telegram открывается **только по HTTPS** (обычный `http://localhost` из Telegram недоступен). В этом репозитории фронтенд ходит в API через **`/api/*`** (rewrite в Next.js на backend), поэтому для теста в Telegram достаточно **одного HTTPS-адреса на порт 3000**.

### 1) Переменные в `.env`

- `TELEGRAM_BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather).
- `WEBAPP_URL` — публичный **HTTPS** URL вашего Next.js (без слэша в конце или со слэшем — бот сам нормализует). Пример: `https://abcd-12.ngrok-free.app`.

**Важно:** не коммитьте реальные токены. Если токен когда-либо попал в git или в чат — отзовите его в BotFather и выдайте новый.

### 2) Туннель на порт 3000 и `WEBAPP_URL` — пошагово

Почему так: клиент Telegram открывает Mini App **только по публичному HTTPS**. Адрес `http://localhost:3000` с телефона недоступен, поэтому нужен **туннель**: внешний `https://…` ведёт на ваш локальный порт **3000** (Next.js). API проксируется с того же домена через `/api/*`, отдельный туннель на 8000 не обязателен.

1. Установите [ngrok](https://ngrok.com/) (или [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), [localtunnel](https://localtunnel.github.io/www/)).
2. В корне репозитория запустите стек: `docker compose up -d` (должны слушать **3000** и **8000** на машине).
3. В **отдельном** терминале выполните: `ngrok http 3000`.
4. В выводе ngrok найдите строку **Forwarding** с **https://** (например `https://abc123.ngrok-free.app`).
5. Откройте файл **`.env`** в корне проекта и пропишите (подставьте свой URL, без пути к странице):
   - `WEBAPP_URL=https://abc123.ngrok-free.app`
6. Сохраните `.env` и перезапустите бота (чтобы подтянулся новый URL):
   - `docker compose up -d --force-recreate telegram-bot`
7. При **смене** URL ngrok (каждый новый запуск в бесплатном режиме часто даёт новый домен) снова обновите `WEBAPP_URL` и снова выполните шаг 6.

**Проверка без Telegram:** в браузере откройте `http://localhost:3000` — интерфейс и `/api` работают локально.

**Проверка с Telegram:** откройте бота → `/start` → кнопка Mini App — должен открыться ваш ngrok-URL.

### 3) Проверка в Telegram

1. Найдите своего бота в Telegram.
2. Отправьте `/start`.
3. Нажмите кнопку **Open Helper** — откроется Mini App.
4. Нажмите **Verify Telegram session** — запрос уйдёт на `POST /telegram/verify-init` (через `/api/...` на фронте).

Опционально в BotFather: **Bot Settings → Menu Button** — укажите тот же URL, что и `WEBAPP_URL`, чтобы кнопка меню всегда открывала приложение.

### 4) Тест на компьютере без Telegram

- UI и API через один origin: откройте `http://localhost:3000` — запросы идут на `/api/...` и проксируются на backend (`API_PROXY_TARGET` в Docker: `http://backend:8000`, локально без Docker: `http://127.0.0.1:8000`).
- Проверка `initData` сработает **только** при открытии страницы из Telegram (кнопка Mini App).
- Прямой смоук API: `curl http://localhost:8000/health` и эндпоинты из списка ниже.

## Local Development (initial)

1. Copy env template:
   - `cp .env.example .env`
2. Заполните `.env` (`TELEGRAM_BOT_TOKEN`, для Telegram — ещё `WEBAPP_URL` после ngrok).
3. Start infrastructure:
   - `docker compose up -d`
4. Verify services:
   - Postgres: `localhost:5432`
   - Redis: `localhost:6379`
   - MinIO API: `localhost:9000`
   - MinIO Console: `localhost:9001`

## Prototype API Endpoints

- `GET /health`
- `GET /meetings`
- `GET /meetings/{id}`
- `GET /meetings/{id}/transcript`
- `GET /meetings/{id}/protocol`
- `POST /meetings/start`
- `POST /meetings/stop`
- `POST /meetings/{id}/transcribe` (multipart with `audio` file; Whisper API if `OPENAI_API_KEY` is set)
- `POST /meetings/{id}/protocol-draft` (stub draft)
- `POST /meetings/{id}/start-demo-flow` (stub chain: transcript + protocol in one call)
- `POST /assistant/execute` (ClawBot integration point + local stub fallback)
- `POST /telegram/verify-init` (проверка `initData` Mini App; с фронта: `POST /api/telegram/verify-init`)

Meeting state, transcript, and protocol draft are now persisted in PostgreSQL.

## Debugging checklist

- Confirm Docker is available: `docker --version` and `docker compose version`.
- Start stack: `docker compose up -d` (from repo root).
- Check containers: `docker compose ps` and `docker logs helper-backend --tail 50` / `docker logs helper-telegram-bot --tail 50`.
- API smoke test:
  - `curl -sS http://localhost:8000/health`
  - `curl -sS -X POST http://localhost:8000/meetings/start -H 'Content-Type: application/json' -d '{"title":"Smoke test"}'`

## Next steps toward a working end-user prototype

- Telegram Bot + Mini App: базовый polling-бот, HTTPS через туннель, проверка `initData` — уже в репо; дальше — webhook на проде и жёсткая привязка сессий к `user.id`.
- Secrets: set `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY` (Whisper API), optional `CLAWBOT_API_URL` / `CLAWBOT_API_KEY` in `.env` and pass into `docker compose`.
- Real audio path: record/upload to object storage (MinIO/S3), store `audio_asset` metadata, run STT as a background job (Celery) with status polling.
- Protocol generation: replace stub with LLM call using stored transcript; add JSON schema validation and versioning on `protocols`.
- Tasks: create `tasks` from confirmed action items; reminders via worker + Telegram send API.
- Hardening: Alembic migrations (replace `create_all`), structured logging, basic auth/rate limits on public API.

## Next

Detailed execution plan and sprint backlog are in:
- `docs/IMPLEMENTATION_PLAN_v0.1.md`
- `docs/NEXT_STEPS.md`

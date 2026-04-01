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

## Доступ с вашего компьютера (localhost)

После `docker compose up -d` откройте в браузере на **той же машине**, где запущен Docker:

| Сервис | URL |
|--------|-----|
| Mini App (UI) | [http://localhost:3000](http://localhost:3000) или [http://127.0.0.1:3000](http://127.0.0.1:3000) |
| Backend API | [http://localhost:8000/health](http://localhost:8000/health) |
| Проверка Whisper (backend → whisper-api) | [http://localhost:8000/health/stt](http://localhost:8000/health/stt) |
| Whisper API | [http://localhost:8100](http://localhost:8100) |
| MinIO (S3) | [http://localhost:9000](http://localhost:9000) |
| MinIO Console | [http://localhost:9001](http://localhost:9001) |

Запросы из браузера на `localhost:3000` идут на API через **тот же origin**: `/api/...` → Next.js проксирует на backend в Docker (`API_PROXY_TARGET`).

Фронт в контейнере запускается как **`next dev -H 0.0.0.0`**, чтобы порт **3000** был доступен с хоста по `localhost` (иначе Next по умолчанию слушал бы только loopback внутри контейнера).

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
   - Whisper API ([Hipc/whisper-api](https://github.com/Hipc/whisper-api)): `localhost:8100`
   - Mini App: `localhost:3000`, Backend: `localhost:8000`

## Self-hosted Whisper (Hipc/whisper-api)

В `docker-compose.yml` добавлен сервис **`whisper-api`** на образе `hipc/whisper-api` (см. [репозиторий](https://github.com/Hipc/whisper-api)). Backend по умолчанию в Compose использует **`STT_PROVIDER=hipc_whisper_api`** и шлёт аудио на `POST /transcribe` (поле `audio_file`), затем опрашивает `GET /task/{task_id}` до готовности.

Переменные (см. `.env.example`):

- `STT_PROVIDER` — `hipc_whisper_api` (локальный Docker) или `openai_whisper_api` (облако OpenAI, нужен `OPENAI_API_KEY`).
- `WHISPER_API_BASE_URL` — в Docker сети по умолчанию `http://whisper-api:8100`; если backend без Docker — `http://localhost:8100`.
- `WHISPER_API_POLL_TIMEOUT` — максимум секунд ожидания результата (по умолчанию `600`).
- `WHISPER_API_LANGUAGE` — опционально код языка для Whisper (query-параметр `language` у Hipc API).

Первый запуск контейнера может занять время: подтягивается модель **Whisper turbo**, нужны **RAM** (ориентир **4+ ГБ** под сервис; на CPU длинные файлы обрабатываются медленно). Логи: `docker logs helper-whisper-api -f`.

Проверка API напрямую:

```bash
curl -sS http://localhost:8100/task/00000000-0000-0000-0000-000000000000
# ожидаемо 404 если задачи нет — значит сервис поднялся
```

## Prototype API Endpoints

- `GET /health`
- `GET /health/stt` (доступен ли Hipc whisper-api для `STT_PROVIDER=hipc_whisper_api`; с фронта: `/api/health/stt`)
- `GET /meetings`
- `GET /meetings/{id}`
- `GET /meetings/{id}/transcript`
- `GET /meetings/{id}/protocol`
- `POST /meetings/start`
- `POST /meetings/stop`
- `POST /meetings/{id}/transcribe` (multipart `audio`; STT: Hipc [whisper-api](https://github.com/Hipc/whisper-api) в Docker или OpenAI при `STT_PROVIDER=openai_whisper_api`)
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
- Secrets: `TELEGRAM_BOT_TOKEN`; для облачного STT — `OPENAI_API_KEY`; локальный Whisper — сервис `whisper-api` + `STT_PROVIDER=hipc_whisper_api`. Опционально `CLAWBOT_*`.
- Real audio path: record/upload to object storage (MinIO/S3), store `audio_asset` metadata, run STT as a background job (Celery) with status polling.
- Protocol generation: replace stub with LLM call using stored transcript; add JSON schema validation and versioning on `protocols`.
- Tasks: create `tasks` from confirmed action items; reminders via worker + Telegram send API.
- Hardening: Alembic migrations (replace `create_all`), structured logging, basic auth/rate limits on public API.

## Next

Detailed execution plan and sprint backlog are in:
- `docs/IMPLEMENTATION_PLAN_v0.1.md`
- `docs/NEXT_STEPS.md`

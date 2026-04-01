# Helper

Helper is a Telegram Mini App + Bot for meeting capture, protocol generation, task tracking, and AI-assisted execution.

## Repository Structure

- `frontend/` - Telegram Mini App (UI).
- `backend/` - API service (meetings, protocols, tasks, auth).
- `worker/` - background jobs (STT, protocol generation, reminders, AI execution).
- `infra/` - infra configs and local ops notes.
- `docs/` - PRD and implementation planning docs.

## Local Development (initial)

1. Copy env template:
   - `cp .env.example .env`
2. Start infrastructure:
   - `docker compose up -d`
3. Verify services:
   - Postgres: `localhost:5432`
   - Redis: `localhost:6379`
   - MinIO API: `localhost:9000`
   - MinIO Console: `localhost:9001`

## Prototype API Endpoints

- `GET /health`
- `POST /meetings/start`
- `POST /meetings/stop`
- `POST /meetings/{id}/transcribe` (multipart with `audio` file; Whisper API if `OPENAI_API_KEY` is set)
- `POST /meetings/{id}/protocol-draft` (stub draft)
- `POST /meetings/{id}/start-demo-flow` (stub chain: transcript + protocol in one call)
- `POST /assistant/execute` (ClawBot integration point + local stub fallback)

Meeting state, transcript, and protocol draft are now persisted in PostgreSQL.

## Next

Detailed execution plan and sprint backlog are in:
- `docs/IMPLEMENTATION_PLAN_v0.1.md`
- `docs/NEXT_STEPS.md`

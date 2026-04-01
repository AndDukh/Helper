# Next Steps Backlog (Execution-Ready)

## Priority 0 - Bootstrap (this week)

- [ ] Create service skeletons:
  - [ ] `frontend` Next.js app.
  - [ ] `backend` FastAPI app.
  - [ ] `worker` Celery app.
- [ ] Add unified `.env` loading approach for backend/worker.
- [ ] Bring up local infra with `docker compose up -d`.
- [ ] Add migration tool (Alembic) and initial schema migration.
- [ ] Add pre-commit and basic CI (lint + test).

## Priority 1 - MVP Sprint 1

- [ ] Telegram auth verification endpoint.
- [ ] Meeting lifecycle endpoints (`start`, `stop`).
- [ ] Audio upload endpoint to MinIO/S3.
- [ ] Queue a test background job and persist status.
- [ ] Frontend: basic meeting control screen.

## Priority 2 - MVP Sprint 2

- [ ] STT integration service + transcript persistence.
- [ ] Protocol generation endpoint with strict schema output.
- [ ] Frontend: protocol review/confirm screen.
- [ ] Convert confirmed action items into tasks.
- [ ] Reminder scheduler and Telegram reminder messages.

## Priority 3 - V2.1 Extensions

- [ ] Manual importance in task model/UI.
- [ ] Source contact/committee and configurable source weights.
- [ ] Priority score formula and task sorting.
- [ ] AI multi-option planning (`quick`, `balanced`, `deep`).
- [ ] Approve-and-execute AI workflow.
- [ ] Result Pack view (`artifact`, `summary`, `sources`, `open questions`).
- [ ] Feedback loop (rating + edits -> personalization context).

## Suggested First 10 Tickets

1. Bootstrap FastAPI app with health endpoint.
2. Bootstrap Next.js mini app shell with Telegram init parsing.
3. Bootstrap Celery worker with Redis broker.
4. Add Postgres models for meetings/audio/transcripts/protocols/tasks.
5. Implement `POST /meetings/start`.
6. Implement `POST /meetings/{id}/stop`.
7. Implement audio upload to object storage.
8. Implement transcription job and status polling endpoint.
9. Implement protocol generation service and persistence.
10. Implement action item confirmation and task creation.

# Implementation Plan v0.1

## 1) Objective

Move from PRD to immediate development readiness with clear scope, stack, boundaries, and sprint execution order.

## 2) MVP Slice (Sprint 1-2)

### Must have
- Meeting start/stop flow from Telegram.
- Audio upload and storage.
- Transcription pipeline (initially can be API-backed).
- Protocol generation (summary, decisions, action items).
- User confirmation/editing of action items.
- Task creation from confirmed items.
- Deadline fields and baseline reminders.

### Deferred to later in V2.1
- Multi-strategy AI planning.
- Full autonomous AI execution via virtual roles.
- Personalization feedback loop.

## 3) Technical Decisions (Initial)

- Frontend: Next.js + TypeScript + Telegram Mini App SDK.
- Backend: FastAPI (Python).
- Worker: Celery + Redis.
- Database: PostgreSQL.
- Object storage: MinIO in local, S3 in production.
- LLM/STT provider strategy:
  - Start with managed APIs for speed.
  - Keep provider abstraction to enable self-hosted Whisper path later.

## 4) System Boundaries

### Frontend
- Authentication via Telegram init data.
- Meeting controls and task/protocol UIs.
- No direct STT/LLM calls from client.

### Backend API
- Owns core entities (meeting, protocol, task, source, reminders).
- Validates and stores AI outputs in strict schema.
- Emits async jobs to worker.

### Worker
- Executes long-running jobs (STT, protocol generation, reminders).
- Runs AI plan/execution tasks in later phase.

## 5) Initial API Contract (MVP)

- `POST /meetings/start`
- `POST /meetings/{id}/stop`
- `POST /meetings/{id}/audio`
- `POST /meetings/{id}/transcribe`
- `POST /meetings/{id}/protocol/generate`
- `POST /protocols/{id}/confirm`
- `GET /tasks`
- `PATCH /tasks/{id}`

## 6) Data Entities (MVP)

- `users`
- `meetings`
- `audio_assets`
- `transcripts`
- `protocols`
- `action_items`
- `tasks`
- `task_reminders`

## 7) Two-Sprint Delivery Plan

### Sprint 1 (Platform + ingestion)
- Set up monorepo structure and service bootstrap.
- Implement Telegram auth handshake (backend verify endpoint).
- Meeting create/start/stop APIs.
- Audio storage integration (MinIO/S3 abstraction).
- Worker queue setup and sample background job.

### Sprint 2 (Protocol + tasks)
- STT integration and transcript persistence.
- Protocol generation service with JSON schema validation.
- Action item confirmation UI/API.
- Task creation from confirmed items.
- Reminder scheduler + Telegram notifications.

## 8) Risks and Mitigations

- STT quality variability:
  - Mitigation: chunking + speaker separation later + manual correction UI.
- Prompt hallucination:
  - Mitigation: schema constraints and mandatory user confirmation gate.
- Token cost growth:
  - Mitigation: chunk-level summarization and cache strategy.
- Legal/privacy constraints:
  - Mitigation: explicit recording consent and retention policy controls.

## 9) Definition of Ready (Before Coding)

- MVP scope approved.
- Stack approved.
- API contract and schema draft approved.
- Environments and secrets strategy defined.
- First 10 backlog tickets created and estimated.

## 10) Definition of Done (for MVP)

- End-to-end flow works:
  - start meeting -> upload audio -> transcript -> protocol -> confirm items -> tasks created.
- Reminders trigger for due tasks.
- Minimal monitoring/logging active for API and worker.

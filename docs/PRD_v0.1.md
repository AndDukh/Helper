# Helper PRD v0.1

## 1. Product Overview

Helper is a Telegram Mini App + Bot for meeting capture and execution:
- record meetings,
- generate structured protocols and assignments,
- confirm assignment correctness with users,
- execute approved tasks via AI assistant,
- remind users about deadlines and priorities.

## 2. Goals and Scope (V2.1)

### Goals
- Reduce manual time for meeting follow-ups.
- Improve assignment execution speed and accountability.
- Provide transparent AI-assisted planning and execution.
- Personalize AI behavior using user feedback loops.

### In Scope
- Meeting audio recording and storage.
- Speech-to-text transcription (Whisper/faster-whisper).
- Auto protocol generation (summary, decisions, assignments).
- User confirmation/editing of assignments.
- Task management with deadlines, reminders, source importance, and manual priority.
- AI planning options and autonomous execution after user approval.
- Result delivery package with logs and evidence.

### Out of Scope (for v0.1)
- Fully autonomous external actions without approval policies.
- Complex enterprise RBAC and SSO.
- Multi-tenant billing and marketplace features.

## 3. Key Personas

- Manager: runs meetings and delegates tasks.
- Team member: receives and tracks assignments.
- Committee/Stakeholder representative: source of high-priority tasks.
- Admin: configures reminder templates, source weights, and policy limits.

## 4. Core Functional Requirements

### FR-1 Meeting Recorder
- Start/stop meeting recording from Telegram Mini App.
- Store audio in object storage and link to meeting entity.

### FR-2 Transcription
- Queue audio for STT and persist transcript.
- Support long meetings via chunking.

### FR-3 Protocol Generator
- Generate:
  - short summary,
  - agreements/decisions,
  - action items (owner, due date, priority, context).

### FR-4 Assignment Confirmation
- User can confirm, edit, or delete each action item.
- Finalized protocol is versioned and immutable for audit.

### FR-5 Task Prioritization and Source Importance
- Task fields:
  - `due_date`, `due_time`, `timezone`,
  - `importance_manual` (Low/Med/High/Critical),
  - `source_contact` or `source_committee`,
  - `source_weight`,
  - `priority_score`.
- Manual importance can always be changed by user.
- Source weight is configurable and included in scoring.

### FR-6 Reminders
- Default schedule: T-48h, T-24h, T-4h, T-1h, overdue +24h.
- User can configure reminder profile per task/project.
- Daily digest in Telegram.

### FR-7 AI Chief of Staff (Plan + Execute)
- AI proposes 2-3 execution strategies per task.
- User selects or edits strategy.
- After user approval, AI assistant executes selected strategy using virtual roles:
  - Researcher, Analyst, Writer, Presenter, Reviewer.
- AI returns Result Pack:
  - completed output artifact,
  - brief outcome summary,
  - sources and assumptions,
  - open questions,
  - execution log.
- User can accept or request rework.

### FR-8 Feedback Learning Loop
- Collect explicit rating and textual feedback.
- Track acceptance/edit/rework signals.
- Adapt future planning/execution style per user preferences.

## 5. Non-Functional Requirements

- Security: encrypted transport, signed webhook verification, role checks.
- Privacy: consent-friendly recording flow; deletion policy support.
- Reliability: retriable background jobs and idempotent task execution.
- Performance:
  - protocol draft within target SLA after transcript is ready,
  - reminders delivered within acceptable notification window.
- Observability: structured logs, task traces, failure alerts.

## 6. Data Model (High-Level)

- `users`
- `meetings`
- `audio_assets`
- `transcripts`
- `protocols` (versioned)
- `action_items`
- `tasks`
- `task_reminders`
- `sources` (contact/committee + weights)
- `ai_plans`
- `ai_executions`
- `result_packs`
- `feedback_events`

## 7. API Surface (High-Level)

- `POST /meetings/start`
- `POST /meetings/{id}/stop`
- `POST /meetings/{id}/transcribe`
- `POST /meetings/{id}/protocol/generate`
- `POST /protocols/{id}/confirm`
- `PATCH /tasks/{id}`
- `POST /tasks/{id}/ai-plan`
- `POST /tasks/{id}/approve-and-execute`
- `GET /tasks/{id}/result`
- `POST /tasks/{id}/feedback`

## 8. User Stories + Acceptance Criteria (Key)

### US-1 Recording and protocol
As a user, I want to record a meeting and automatically receive a draft protocol.
- AC: after stop event, transcript and protocol draft are generated and visible.

### US-2 Assignment correctness confirmation
As a user, I want to confirm and fix action items before they become tasks.
- AC: each action item supports edit/delete/confirm; only confirmed items become tasks.

### US-3 Deadline reminders
As a user, I want reminders before deadlines and on overdue tasks.
- AC: reminders fire on configured schedule and include quick actions.

### US-4 Manual importance
As a user, I want to set task importance manually.
- AC: changing manual importance immediately updates priority ordering.

### US-5 Source importance
As a user, I want to track whether task came from a contact or committee and factor this into priority.
- AC: source is stored per task; source weight influences `priority_score`.

### US-6 AI proposes plans
As a user, I want AI to propose execution options.
- AC: at least 2 plan options are shown with rationale and expected output.

### US-7 AI executes approved plan
As a user, I want AI to execute the selected plan after my confirmation.
- AC: clicking "Approve and Execute" starts execution automatically and sets task status to `executing`.

### US-8 AI shows final result
As a user, I want to see completed AI output in a structured result package.
- AC: result view includes artifact, summary, sources, assumptions, and open questions; user can accept or request rework.

### US-9 Learning from feedback
As a user, I want AI to improve based on my feedback.
- AC: feedback is stored and used in subsequent plan/execution prompts for that user.

## 9. KPI Targets (V2.1)

- Protocol generation adoption rate.
- On-time completion rate.
- Plan acceptance rate (without edits).
- First-pass acceptance of AI results.
- Average time from assignment confirmation to first usable draft.

## 10. Delivery Milestones

- M1: Meetings core (recording, transcript, protocol, confirmation).
- M2: Tasks core (deadlines, reminders, manual/source importance, scoring).
- M3: AI executor baseline (research/memo/slides + result pack).
- M4: AI Chief of Staff (multi-option planning + approve-and-execute).
- M5: Feedback learning loop and quality analytics.

## 11. Definition of Done (V2.1)

- All FR-1..FR-8 implemented and tested at API and UX levels.
- End-to-end flow works:
  - meeting recording -> protocol -> confirm items -> task priority/reminders -> AI plan -> approve and execute -> result shown.
- Monitoring dashboards and alerting are active.
- Security and privacy checks documented.

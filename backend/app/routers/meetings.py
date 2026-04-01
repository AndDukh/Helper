from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from ..schemas import (
    MeetingResponse,
    MeetingStartRequest,
    MeetingStopRequest,
    ProtocolDraftResponse,
)

router = APIRouter()
MEETINGS: dict[UUID, MeetingResponse] = {}


@router.post("/start", response_model=MeetingResponse)
def start_meeting(payload: MeetingStartRequest) -> MeetingResponse:
    meeting = MeetingResponse(
        id=uuid4(),
        title=payload.title,
        status="recording",
        started_at=datetime.now(tz=timezone.utc),
    )
    MEETINGS[meeting.id] = meeting
    return meeting


@router.post("/stop", response_model=MeetingResponse)
def stop_meeting(payload: MeetingStopRequest) -> MeetingResponse:
    meeting = MEETINGS.get(payload.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status == "stopped":
        return meeting

    meeting.status = "stopped"
    meeting.stopped_at = datetime.now(tz=timezone.utc)
    return meeting


@router.post("/{meeting_id}/protocol-draft", response_model=ProtocolDraftResponse)
def generate_protocol_stub(meeting_id: UUID) -> ProtocolDraftResponse:
    meeting = MEETINGS.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return ProtocolDraftResponse(
        meeting_id=meeting_id,
        summary=f"Draft summary for '{meeting.title}'.",
        decisions=[
            "Ship MVP meeting flow in sprint 1-2.",
            "Validate reminder UX with pilot users.",
        ],
        action_items=[
            {"owner": "and", "task": "Finalize API contracts", "due_date": "2026-04-05"},
            {"owner": "team", "task": "Prepare demo flow", "due_date": "2026-04-08"},
        ],
    )

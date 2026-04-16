from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Meeting, Protocol, Transcript
from ..schemas import (
    AutoProtocolResponse,
    DemoFlowResponse,
    MeetingResponse,
    MeetingStartRequest,
    MeetingStopRequest,
    ProtocolDraftResponse,
    TranscriptResponse,
)
from ..services.stt_service import STTService

router = APIRouter()
stt_service = STTService()


def _to_meeting_response(meeting: Meeting) -> MeetingResponse:
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        status=meeting.status,
        started_at=meeting.started_at,
        stopped_at=meeting.stopped_at,
    )


def _build_protocol_stub(meeting_id: UUID, title: str) -> ProtocolDraftResponse:
    return ProtocolDraftResponse(
        meeting_id=meeting_id,
        summary=f"Draft summary for '{title}'.",
        decisions=[
            "Ship MVP meeting flow in sprint 1-2.",
            "Validate reminder UX with pilot users.",
        ],
        action_items=[
            {"owner": "and", "task": "Finalize API contracts", "due_date": "2026-04-05"},
            {"owner": "team", "task": "Prepare demo flow", "due_date": "2026-04-08"},
        ],
    )


def _upsert_transcript(db: Session, meeting_id: UUID, transcript_text: str) -> None:
    transcript_row = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if transcript_row:
        transcript_row.transcript_text = transcript_text
        return

    db.add(Transcript(meeting_id=meeting_id, transcript_text=transcript_text))


def _upsert_protocol(db: Session, payload: ProtocolDraftResponse) -> None:
    protocol_row = db.query(Protocol).filter(Protocol.meeting_id == payload.meeting_id).first()
    if protocol_row:
        protocol_row.summary = payload.summary
        protocol_row.decisions = payload.decisions
        protocol_row.action_items = payload.action_items
        return

    db.add(
        Protocol(
            meeting_id=payload.meeting_id,
            summary=payload.summary,
            decisions=payload.decisions,
            action_items=payload.action_items,
        )
    )


@router.get("", response_model=list[MeetingResponse])
def list_meetings(db: Session = Depends(get_db)) -> list[MeetingResponse]:
    meetings = db.query(Meeting).order_by(Meeting.started_at.desc()).all()
    return [_to_meeting_response(meeting) for meeting in meetings]


@router.post("/start", response_model=MeetingResponse)
def start_meeting(payload: MeetingStartRequest, db: Session = Depends(get_db)) -> MeetingResponse:
    meeting = Meeting(
        title=payload.title,
        status="recording",
        started_at=datetime.now(tz=timezone.utc),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _to_meeting_response(meeting)


@router.post("/stop", response_model=MeetingResponse)
def stop_meeting(payload: MeetingStopRequest, db: Session = Depends(get_db)) -> MeetingResponse:
    meeting = db.get(Meeting, payload.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status == "stopped":
        return _to_meeting_response(meeting)

    meeting.status = "stopped"
    meeting.stopped_at = datetime.now(tz=timezone.utc)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _to_meeting_response(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: UUID, db: Session = Depends(get_db)) -> MeetingResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _to_meeting_response(meeting)


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
def get_meeting_transcript(meeting_id: UUID, db: Session = Depends(get_db)) -> TranscriptResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript_row = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript_row:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return TranscriptResponse(meeting_id=meeting_id, transcript_text=transcript_row.transcript_text)


@router.get("/{meeting_id}/protocol", response_model=ProtocolDraftResponse)
def get_meeting_protocol(meeting_id: UUID, db: Session = Depends(get_db)) -> ProtocolDraftResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    protocol_row = db.query(Protocol).filter(Protocol.meeting_id == meeting_id).first()
    if not protocol_row:
        raise HTTPException(status_code=404, detail="Protocol not found")

    return ProtocolDraftResponse(
        meeting_id=meeting_id,
        summary=protocol_row.summary,
        decisions=protocol_row.decisions,
        action_items=protocol_row.action_items,
    )


@router.post("/{meeting_id}/protocol-draft", response_model=ProtocolDraftResponse)
def generate_protocol_stub(meeting_id: UUID, db: Session = Depends(get_db)) -> ProtocolDraftResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    protocol_payload = _build_protocol_stub(meeting_id=meeting_id, title=meeting.title)
    _upsert_protocol(db, protocol_payload)
    db.commit()
    return protocol_payload


@router.post("/{meeting_id}/transcribe", response_model=TranscriptResponse)
async def transcribe_meeting_audio(
    meeting_id: UUID, audio: UploadFile = File(...), db: Session = Depends(get_db)
) -> TranscriptResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    try:
        transcript = await stt_service.transcribe(
            filename=audio.filename or "meeting_audio.webm",
            content=content,
            content_type=audio.content_type,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Speech service unreachable or error: {exc!s}",
        ) from exc
    _upsert_transcript(db, meeting_id, transcript)
    db.commit()
    return TranscriptResponse(meeting_id=meeting_id, transcript_text=transcript)


@router.post("/{meeting_id}/auto-protocol", response_model=AutoProtocolResponse)
async def transcribe_and_build_protocol(
    meeting_id: UUID, audio: UploadFile = File(...), db: Session = Depends(get_db)
) -> AutoProtocolResponse:
    transcript = await transcribe_meeting_audio(meeting_id=meeting_id, audio=audio, db=db)
    protocol = generate_protocol_stub(meeting_id=meeting_id, db=db)
    return AutoProtocolResponse(meeting_id=meeting_id, transcript=transcript, protocol=protocol)


@router.post("/{meeting_id}/start-demo-flow", response_model=DemoFlowResponse)
def start_demo_flow(meeting_id: UUID, db: Session = Depends(get_db)) -> DemoFlowResponse:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = TranscriptResponse(
        meeting_id=meeting_id,
        transcript_text=(
            f"Demo transcript for '{meeting.title}'. "
            "Configured for prototype flow without uploading real audio."
        ),
    )
    _upsert_transcript(db, meeting_id, transcript.transcript_text)

    protocol = _build_protocol_stub(meeting_id=meeting_id, title=meeting.title)
    _upsert_protocol(db, protocol)
    db.commit()

    meeting_response = _to_meeting_response(meeting)
    return DemoFlowResponse(meeting=meeting_response, transcript=transcript, protocol=protocol)

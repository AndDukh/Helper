from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MeetingStartRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)


class MeetingStopRequest(BaseModel):
    meeting_id: UUID


class MeetingResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    status: Literal["recording", "stopped"]
    started_at: datetime
    stopped_at: datetime | None = None


class ProtocolDraftResponse(BaseModel):
    meeting_id: UUID
    summary: str
    decisions: list[str]
    action_items: list[dict[str, str]]


class TranscriptResponse(BaseModel):
    meeting_id: UUID
    transcript_text: str


class AssistantExecuteRequest(BaseModel):
    task: str = Field(min_length=3, max_length=1000)
    context: str | None = None


class AssistantExecuteResponse(BaseModel):
    provider: str
    status: str
    summary: str
    artifact: str

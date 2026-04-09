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
    provider: str | None = None


class AssistantExecuteResponse(BaseModel):
    provider: str
    status: str
    summary: str
    artifact: str


class DemoFlowResponse(BaseModel):
    meeting: MeetingResponse
    transcript: TranscriptResponse
    protocol: ProtocolDraftResponse


class IntegrationConnectRequest(BaseModel):
    service: str = Field(min_length=2, max_length=64)


class IntegrationConnectResponse(BaseModel):
    service: str
    status: str
    auth_url: str | None = None
    note: str


class IntegrationItem(BaseModel):
    service: str
    connected: bool


class IntegrationUploadRequest(BaseModel):
    service: str = Field(min_length=2, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=128)
    content_base64: str = Field(min_length=8)
    folder: str | None = None


class IntegrationUploadResponse(BaseModel):
    service: str
    status: str
    location: str | None = None
    note: str


class AIProviderConnectRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=64)
    api_key: str | None = None


class AIProviderConnectResponse(BaseModel):
    provider: str
    status: str
    note: str


class ProtocolTaskExecuteRequest(BaseModel):
    meeting_id: UUID
    task: str = Field(min_length=3, max_length=1000)
    provider: str = Field(default="kimi", min_length=2, max_length=64)


class ProtocolTaskExecuteResponse(BaseModel):
    meeting_id: UUID
    provider: str
    status: str
    summary: str
    artifact: str


class AutoProtocolResponse(BaseModel):
    meeting_id: UUID
    transcript: TranscriptResponse
    protocol: ProtocolDraftResponse

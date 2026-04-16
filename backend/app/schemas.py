from datetime import datetime
from typing import Dict, Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MeetingStartRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)


class MeetingStopRequest(BaseModel):
    meeting_id: UUID


class MeetingResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    status: Literal["recording", "stopped"]
    started_at: datetime
    stopped_at: Optional[datetime] = None


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
    context: Optional[str] = None
    provider: Optional[str] = None


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
    auth_url: Optional[str] = None
    note: str


class IntegrationItem(BaseModel):
    service: str
    connected: bool


class IntegrationUploadRequest(BaseModel):
    service: str = Field(min_length=2, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=128)
    content_base64: str = Field(min_length=8)
    folder: Optional[str] = None


class IntegrationUploadResponse(BaseModel):
    service: str
    status: str
    location: Optional[str] = None
    note: str


class AIProviderConnectRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=64)
    api_key: Optional[str] = None


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


class OrchestrateRequest(BaseModel):
    task_type: Literal["chat", "todo", "note", "analysis", "plan", "extract", "report", "presentation", "data_analysis"] = "chat"
    prompt: str = Field(min_length=3, max_length=12000)
    context: Optional[Dict] = None
    priority: Literal["low", "normal", "high"] = "normal"
    force_provider: Optional[Literal["ollama", "kimi"]] = None


class OrchestrateArtifact(BaseModel):
    type: str
    content: Union[str, Dict]


class OrchestrateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider_used: str
    model_used: Optional[str] = None
    trace_id: str
    route_reason: str
    result: dict
    artifacts: list[OrchestrateArtifact]

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Meeting, Protocol
from ..schemas import (
    AIProviderConnectRequest,
    AIProviderConnectResponse,
    AssistantExecuteRequest,
    AssistantExecuteResponse,
    IntegrationConnectRequest,
    IntegrationConnectResponse,
    IntegrationItem,
    IntegrationUploadRequest,
    IntegrationUploadResponse,
    ProtocolTaskExecuteRequest,
    ProtocolTaskExecuteResponse,
)
from ..services.assistant_service import AssistantService
from ..services.integration_service import IntegrationService

router = APIRouter()
assistant_service = AssistantService()
integration_service = IntegrationService()

SUPPORTED_INTEGRATIONS = {
    "google_calendar",
    "outlook_calendar",
    "google_drive",
    "dropbox",
    "onedrive",
    "box",
}
SUPPORTED_AI_PROVIDERS = {"kimi", "openai", "claude", "gemini"}


@router.post("/execute", response_model=AssistantExecuteResponse)
async def execute_task(payload: AssistantExecuteRequest) -> AssistantExecuteResponse:
    if payload.provider:
        result = await assistant_service.execute_with_provider(
            task=payload.task, provider=payload.provider, context=payload.context
        )
    else:
        result = await assistant_service.execute(task=payload.task, context=payload.context)
    return AssistantExecuteResponse(**result)


@router.get("/integrations", response_model=list[IntegrationItem])
def list_integrations(db: Session = Depends(get_db)) -> list[IntegrationItem]:
    return [
        IntegrationItem(service=service, connected=integration_service.is_connected(db, service))
        for service in sorted(SUPPORTED_INTEGRATIONS)
    ]


@router.post("/integrations/connect", response_model=IntegrationConnectResponse)
def connect_integration(payload: IntegrationConnectRequest) -> IntegrationConnectResponse:
    service = payload.service.strip().lower()
    if service not in SUPPORTED_INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported integration service: {service}")
    result = integration_service.connect(service)
    return IntegrationConnectResponse(**result)


@router.post("/integrations/upload", response_model=IntegrationUploadResponse)
async def upload_material(
    payload: IntegrationUploadRequest, db: Session = Depends(get_db)
) -> IntegrationUploadResponse:
    service = payload.service.strip().lower()
    if service not in SUPPORTED_INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported integration service: {service}")
    try:
        result = await integration_service.upload_material(
            db=db,
            service=service,
            filename=payload.filename,
            mime_type=payload.mime_type,
            content_base64=payload.content_base64,
            folder=payload.folder,
        )
        return IntegrationUploadResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 content: {exc!s}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upload failed: {exc!s}") from exc


@router.get("/integrations/oauth/{service}/callback", response_model=IntegrationConnectResponse)
async def oauth_callback(
    service: str, code: str = Query(..., min_length=3), db: Session = Depends(get_db)
) -> IntegrationConnectResponse:
    normalized = service.strip().lower()
    if normalized not in SUPPORTED_INTEGRATIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported integration service: {normalized}")
    try:
        result = await integration_service.exchange_oauth_code(db, normalized, code)
        return IntegrationConnectResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OAuth exchange failed: {exc!s}") from exc


@router.post("/providers/connect", response_model=AIProviderConnectResponse)
def connect_provider(payload: AIProviderConnectRequest) -> AIProviderConnectResponse:
    provider = payload.provider.strip().lower()
    if provider not in SUPPORTED_AI_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported AI provider: {provider}")
    return AIProviderConnectResponse(
        provider=provider,
        status="connected" if payload.api_key else "auth_required",
        note="MVP mode: provider is registered. Add API key to enable real execution.",
    )


@router.post("/protocol/execute-task", response_model=ProtocolTaskExecuteResponse)
async def execute_protocol_task(
    payload: ProtocolTaskExecuteRequest, db: Session = Depends(get_db)
) -> ProtocolTaskExecuteResponse:
    meeting = db.get(Meeting, payload.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    protocol = db.query(Protocol).filter(Protocol.meeting_id == payload.meeting_id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")

    result = await assistant_service.execute_with_provider(
        task=payload.task,
        provider=payload.provider,
        context=f"Meeting: {meeting.title}. Protocol summary: {protocol.summary}",
    )
    return ProtocolTaskExecuteResponse(
        meeting_id=payload.meeting_id,
        provider=result["provider"],
        status=result["status"],
        summary=result["summary"],
        artifact=result["artifact"],
    )

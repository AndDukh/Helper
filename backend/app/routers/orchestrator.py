from uuid import uuid4

from fastapi import APIRouter

from ..schemas import OrchestrateRequest, OrchestrateResponse
from ..services.orchestration_service import OrchestrationService

router = APIRouter()
orchestration_service = OrchestrationService()


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_task(payload: OrchestrateRequest) -> OrchestrateResponse:
    execution = await orchestration_service.run(
        task_type=payload.task_type,
        prompt=payload.prompt,
        context=payload.context,
        priority=payload.priority,
        force_provider=payload.force_provider,
    )

    return OrchestrateResponse(
        provider_used=execution.get("provider", "ollama"),
        model_used=execution.get("model_used"),
        trace_id=str(uuid4()),
        route_reason=execution.get("route_reason", "unknown"),
        result=execution.get("result", {}),
        artifacts=execution.get("artifacts", []),
    )

from fastapi import APIRouter

from ..schemas import AssistantExecuteRequest, AssistantExecuteResponse
from ..services.assistant_service import AssistantService

router = APIRouter()
assistant_service = AssistantService()


@router.post("/execute", response_model=AssistantExecuteResponse)
async def execute_task(payload: AssistantExecuteRequest) -> AssistantExecuteResponse:
    result = await assistant_service.execute(task=payload.task, context=payload.context)
    return AssistantExecuteResponse(**result)

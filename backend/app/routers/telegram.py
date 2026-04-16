from __future__ import annotations

import json
import os
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.telegram_auth import verify_telegram_init_data

router = APIRouter()


class TelegramVerifyRequest(BaseModel):
    init_data: str = Field(min_length=10)


class TelegramVerifyResponse(BaseModel):
    ok: bool
    user: Optional[Dict] = None


@router.post("/verify-init", response_model=TelegramVerifyResponse)
def verify_init(payload: TelegramVerifyRequest) -> TelegramVerifyResponse:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is not configured on server")

    try:
        data = verify_telegram_init_data(payload.init_data, token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_raw = data.get("user")
    user: Optional[Dict] = None
    if user_raw:
        try:
            user = json.loads(user_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="user field is not valid JSON") from exc

    return TelegramVerifyResponse(ok=True, user=user)

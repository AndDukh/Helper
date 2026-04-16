from __future__ import annotations

import os
import tempfile
from typing import Any

import httpx


class STTService:
    _whisper_model: Any = None

    def __init__(self) -> None:
        self.provider = os.getenv("STT_PROVIDER", "openai_whisper_local")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.whisper_model_name = os.getenv("WHISPER_MODEL", "small").strip() or "small"

    async def transcribe(self, filename: str, content: bytes, content_type: str | None) -> str:
        if self.provider == "openai_whisper_local":
            return await self._transcribe_local_whisper(filename, content)

        if self.provider == "openai_whisper_api" and self.openai_api_key:
            return await self._transcribe_openai(filename, content, content_type)

        # Fallback stub for local development without API key.
        return (
            "Stub transcript: set STT_PROVIDER=openai_whisper_local (recommended) "
            "or OPENAI_API_KEY for OpenAI Whisper API."
        )

    async def _transcribe_openai(self, filename: str, content: bytes, content_type: str | None) -> str:
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}
        files = {"file": (filename, content, content_type or "application/octet-stream")}
        data = {"model": "whisper-1", "response_format": "text"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.text.strip()

    async def _transcribe_local_whisper(self, filename: str, content: bytes) -> str:
        try:
            import whisper
        except Exception as exc:
            raise RuntimeError(
                "Local Whisper is not available. Install openai-whisper and ffmpeg."
            ) from exc

        if STTService._whisper_model is None:
            STTService._whisper_model = whisper.load_model(self.whisper_model_name)

        suffix = ""
        if "." in filename:
            suffix = filename[filename.rfind(".") :]
        if not suffix:
            suffix = ".webm"

        with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
            tmp.write(content)
            tmp.flush()
            result = STTService._whisper_model.transcribe(tmp.name)
            text = (result.get("text") or "").strip()
            return text if text else "(empty transcript)"

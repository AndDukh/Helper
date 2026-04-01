import asyncio
import os
import time

import httpx


class STTService:
    def __init__(self) -> None:
        self.provider = os.getenv("STT_PROVIDER", "openai_whisper_api")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.whisper_api_base = os.getenv("WHISPER_API_BASE_URL", "http://whisper-api:8100").rstrip("/")
        self.whisper_poll_seconds = float(os.getenv("WHISPER_API_POLL_TIMEOUT", "600"))

    async def transcribe(self, filename: str, content: bytes, content_type: str | None) -> str:
        if self.provider == "hipc_whisper_api":
            return await self._transcribe_hipc_whisper_api(filename, content, content_type)

        if self.provider == "openai_whisper_api" and self.openai_api_key:
            return await self._transcribe_openai(filename, content, content_type)

        # Fallback stub for local development without API key.
        return (
            "Stub transcript: set STT_PROVIDER=hipc_whisper_api (with whisper-api container) "
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

    async def _transcribe_hipc_whisper_api(
        self, filename: str, content: bytes, content_type: str | None
    ) -> str:
        """
        Self-hosted Whisper REST API (async job + poll), e.g. https://github.com/Hipc/whisper-api
        """
        base = self.whisper_api_base
        language = os.getenv("WHISPER_API_LANGUAGE", "").strip() or None

        params = {"language": language} if language else None
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {"audio_file": (filename, content, content_type or "application/octet-stream")}
            response = await client.post(f"{base}/transcribe", files=files, params=params)
            response.raise_for_status()
            payload = response.json()
            task_id = payload.get("task_id")
            if not task_id:
                raise RuntimeError("whisper-api: missing task_id in response")

        deadline = time.monotonic() + self.whisper_poll_seconds
        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.monotonic() < deadline:
                await asyncio.sleep(0.5)
                response = await client.get(f"{base}/task/{task_id}")
                response.raise_for_status()
                body = response.json()
                data = body.get("data") or {}
                status = data.get("status")
                if status == "completed":
                    result = data.get("result") or {}
                    text = (result.get("text") or "").strip()
                    return text if text else "(empty transcript)"
                if status == "failed":
                    err = data.get("error") or "transcription failed"
                    raise RuntimeError(f"whisper-api: {err}")

        raise TimeoutError(f"whisper-api: timeout after {self.whisper_poll_seconds}s for task {task_id}")

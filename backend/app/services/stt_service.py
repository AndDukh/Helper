import os

import httpx


class STTService:
    def __init__(self) -> None:
        self.provider = os.getenv("STT_PROVIDER", "openai_whisper_api")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    async def transcribe(self, filename: str, content: bytes, content_type: str | None) -> str:
        if self.provider == "openai_whisper_api" and self.openai_api_key:
            return await self._transcribe_openai(filename, content, content_type)

        # Fallback stub for local development without API key.
        return "Stub transcript: configure OPENAI_API_KEY to use Whisper API."

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

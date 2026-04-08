import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

# Transient HTTP status codes that are safe to retry.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class STTService:
    def __init__(self) -> None:
        self.provider = os.getenv("STT_PROVIDER", "openai_whisper_api")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.whisper_api_base = os.getenv("WHISPER_API_BASE_URL", "http://whisper-api:8100").rstrip("/")
        self.whisper_poll_seconds = float(os.getenv("WHISPER_API_POLL_TIMEOUT", "600"))

        # Retry configuration — tunable via environment variables.
        self.max_submit_retries = int(os.getenv("WHISPER_API_MAX_RETRIES", "3"))
        self.max_poll_retries = int(os.getenv("WHISPER_API_MAX_POLL_RETRIES", "5"))
        self.retry_delay = float(os.getenv("WHISPER_API_RETRY_DELAY", "1.0"))

        # Shared connection limits for all Whisper API clients.
        self._limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def transcribe(self, filename: str, content: bytes, content_type: str | None) -> str:
        if self.provider == "hipc_whisper_api":
            return await self._transcribe_hipc_whisper_api(filename, content, content_type)

        if self.provider == "openai_whisper_api" and self.openai_api_key:
            return await self._transcribe_openai(filename, content, content_type)

        # Fallback stub for local development without API key.
        logger.warning(
            "No STT provider configured. Set STT_PROVIDER=hipc_whisper_api or OPENAI_API_KEY. "
            "Returning stub transcript."
        )
        return (
            "Stub transcript: set STT_PROVIDER=hipc_whisper_api (with whisper-api container) "
            "or OPENAI_API_KEY for OpenAI Whisper API."
        )

    # ------------------------------------------------------------------
    # OpenAI Whisper
    # ------------------------------------------------------------------

    async def _transcribe_openai(self, filename: str, content: bytes, content_type: str | None) -> str:
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}
        files = {"file": (filename, content, content_type or "application/octet-stream")}
        data = {"model": "whisper-1", "response_format": "text"}

        logger.info("Submitting audio to OpenAI Whisper API (file=%s, size=%d bytes)", filename, len(content))
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            transcript = response.text.strip()
            logger.info("OpenAI Whisper transcription complete (chars=%d)", len(transcript))
            return transcript

    # ------------------------------------------------------------------
    # Hipc self-hosted Whisper API
    # ------------------------------------------------------------------

    async def _transcribe_hipc_whisper_api(
        self, filename: str, content: bytes, content_type: str | None
    ) -> str:
        """
        Self-hosted Whisper REST API (async job + poll), e.g. https://github.com/Hipc/whisper-api.

        Submission is retried up to ``max_submit_retries`` times with exponential backoff on
        transient errors.  Each individual poll request is retried up to ``max_poll_retries``
        times before the error is propagated.
        """
        task_id = await self._submit_transcription(filename, content, content_type)
        return await self._poll_transcription(task_id)

    async def _submit_transcription(
        self, filename: str, content: bytes, content_type: str | None
    ) -> str:
        """POST /transcribe with retry + exponential backoff. Returns the task_id."""
        base = self.whisper_api_base
        language = os.getenv("WHISPER_API_LANGUAGE", "").strip() or None
        params = {"language": language} if language else None
        files = {"audio_file": (filename, content, content_type or "application/octet-stream")}

        last_exc: Exception | None = None
        for attempt in range(1, self.max_submit_retries + 2):  # +2: attempt 1…N+1
            try:
                logger.info(
                    "Submitting audio to Whisper API (file=%s, size=%d bytes, attempt=%d/%d)",
                    filename,
                    len(content),
                    attempt,
                    self.max_submit_retries + 1,
                )
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=5.0),
                    limits=self._limits,
                ) as client:
                    response = await client.post(f"{base}/transcribe", files=files, params=params)

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        f"Retryable HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                payload = response.json()
                task_id = payload.get("task_id")
                if not task_id:
                    raise RuntimeError(
                        f"whisper-api: missing task_id in /transcribe response (body={payload!r})"
                    )

                logger.info("Whisper API accepted task (task_id=%s)", task_id)
                return task_id

            except (httpx.TransportError, httpx.HTTPStatusError, RuntimeError) as exc:
                last_exc = exc
                if attempt <= self.max_submit_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Whisper API submit failed (attempt=%d/%d, error=%s). "
                        "Retrying in %.1fs…",
                        attempt,
                        self.max_submit_retries + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Whisper API submit failed after %d attempts: %s",
                        self.max_submit_retries + 1,
                        exc,
                    )

        raise RuntimeError(
            f"whisper-api: failed to submit transcription after {self.max_submit_retries + 1} "
            f"attempts: {last_exc}"
        ) from last_exc

    async def _poll_transcription(self, task_id: str) -> str:
        """Poll GET /task/{task_id} until completed/failed or the deadline is reached."""
        base = self.whisper_api_base
        deadline = time.monotonic() + self.whisper_poll_seconds
        poll_count = 0

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=5.0, pool=5.0),
            limits=self._limits,
        ) as client:
            while time.monotonic() < deadline:
                await asyncio.sleep(0.5)
                poll_count += 1

                status_text, result = await self._fetch_task_status(
                    client, task_id, poll_count
                )

                if status_text == "completed":
                    text = (result.get("text") or "").strip()
                    logger.info(
                        "Whisper API task completed (task_id=%s, polls=%d, chars=%d)",
                        task_id,
                        poll_count,
                        len(text),
                    )
                    return text if text else "(empty transcript)"

                if status_text == "failed":
                    err = result.get("error") or "transcription failed"
                    logger.error(
                        "Whisper API task failed (task_id=%s, polls=%d, error=%s)",
                        task_id,
                        poll_count,
                        err,
                    )
                    raise RuntimeError(f"whisper-api: {err}")

                if poll_count % 20 == 0:
                    elapsed = self.whisper_poll_seconds - (deadline - time.monotonic())
                    logger.debug(
                        "Whisper API task still pending (task_id=%s, polls=%d, elapsed=%.0fs)",
                        task_id,
                        poll_count,
                        elapsed,
                    )

        raise TimeoutError(
            f"whisper-api: task {task_id} did not complete within {self.whisper_poll_seconds:.0f}s "
            f"({poll_count} polls)"
        )

    async def _fetch_task_status(
        self,
        client: httpx.AsyncClient,
        task_id: str,
        poll_count: int,
    ) -> tuple[str | None, dict]:
        """
        Fetch the current status of a Whisper task with per-poll retry logic.

        Returns ``(status, result_dict)`` where *status* is the string from the API
        (e.g. ``"completed"``, ``"failed"``, ``"pending"``) and *result_dict* is the
        ``data`` sub-object (may be empty).
        """
        base = self.whisper_api_base
        last_exc: Exception | None = None

        for attempt in range(1, self.max_poll_retries + 2):
            try:
                response = await client.get(f"{base}/task/{task_id}")

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        f"Retryable HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                body = response.json()
                data: dict = body.get("data") or {}
                return data.get("status"), data

            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt <= self.max_poll_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Whisper API poll failed (task_id=%s, poll=%d, attempt=%d/%d, error=%s). "
                        "Retrying in %.1fs…",
                        task_id,
                        poll_count,
                        attempt,
                        self.max_poll_retries + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Whisper API poll failed after %d attempts (task_id=%s, poll=%d): %s",
                        self.max_poll_retries + 1,
                        task_id,
                        poll_count,
                        exc,
                    )

        raise RuntimeError(
            f"whisper-api: polling task {task_id} failed after {self.max_poll_retries + 1} "
            f"attempts on poll #{poll_count}: {last_exc}"
        ) from last_exc

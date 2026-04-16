from __future__ import annotations

import os

import httpx


class AssistantService:
    def __init__(self) -> None:
        self.clawbot_api_url = os.getenv("CLAWBOT_API_URL", "").rstrip("/")
        self.clawbot_api_key = os.getenv("CLAWBOT_API_KEY", "")
        self.kimi_api_key = os.getenv("KIMI_API_KEY", "").strip()
        self.kimi_api_base_url = os.getenv("KIMI_API_BASE_URL", "https://api.moonshot.ai/v1").rstrip("/")
        self.kimi_model = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

    async def execute(self, task: str, context: str | None = None) -> dict[str, str]:
        # If ClawBot is configured, call it as an external provider.
        if self.clawbot_api_url and self.clawbot_api_key:
            return await self._execute_clawbot(task, context)

        # Local fallback: deterministic prototype response.
        return {
            "provider": "stub",
            "status": "result_ready",
            "summary": f"Prototype execution for task: {task}",
            "artifact": "Draft result package (stub).",
        }

    async def execute_with_provider(
        self, task: str, provider: str, context: str | None = None
    ) -> dict[str, str]:
        normalized = provider.strip().lower()
        if normalized in {"kimi", "moonshot"}:
            return await self._execute_kimi(task=task, context=context)
        if normalized == "external":
            return {
                "provider": "external",
                "status": "auth_required",
                "summary": "External provider is selected but not configured.",
                "artifact": "Configure provider credentials and endpoint.",
            }
        return await self.execute(task=task, context=context)

    async def _execute_kimi(self, task: str, context: str | None) -> dict[str, str]:
        if not self.kimi_api_key:
            return {
                "provider": "kimi",
                "status": "auth_required",
                "summary": "Kimi API key is not configured.",
                "artifact": "Set KIMI_API_KEY in backend environment variables.",
            }

        system_prompt = (
            "You are an executive assistant. Return practical deliverables for a business meeting task. "
            "Always provide: 1) deep research brief, 2) presentation outline, 3) supporting note with next steps."
        )
        user_payload = (
            f"Task:\n{task}\n\n"
            f"Context:\n{context or 'No additional context'}\n\n"
            "Return concise and actionable output."
        )
        payload = {
            "model": self.kimi_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.kimi_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.kimi_api_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return {
                "provider": "kimi",
                "status": "error",
                "summary": f"Kimi request failed: {exc!s}",
                "artifact": "",
            }

        choices = data.get("choices") or []
        message = ""
        if choices and isinstance(choices, list):
            message = ((choices[0] or {}).get("message") or {}).get("content") or ""
        message = message.strip()
        if not message:
            message = "Kimi returned an empty response."

        return {
            "provider": "kimi",
            "status": "result_ready",
            "summary": "Kimi task completed.",
            "artifact": message,
        }

    async def _execute_clawbot(self, task: str, context: str | None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.clawbot_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"task": task, "context": context or ""}

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.clawbot_api_url}/execute", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return {
            "provider": "clawbot",
            "status": data.get("status", "result_ready"),
            "summary": data.get("summary", ""),
            "artifact": data.get("artifact", ""),
        }

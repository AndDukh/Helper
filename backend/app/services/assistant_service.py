import os

import httpx


class AssistantService:
    def __init__(self) -> None:
        self.clawbot_api_url = os.getenv("CLAWBOT_API_URL", "").rstrip("/")
        self.clawbot_api_key = os.getenv("CLAWBOT_API_KEY", "")

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

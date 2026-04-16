from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal

import httpx

ProviderName = Literal["ollama", "kimi"]


@dataclass
class RouteDecision:
    provider: ProviderName
    model: str
    reason: str


class OrchestrationService:
    def __init__(self) -> None:
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_chat_model = os.getenv("OLLAMA_CHAT_MODEL", "llama3.3:latest")
        self.ollama_todo_model = os.getenv("OLLAMA_TODO_MODEL", "phi3:mini")
        self.kimi_api_key = os.getenv("KIMI_API_KEY", "").strip()
        self.kimi_api_base_url = os.getenv("KIMI_API_BASE_URL", "https://api.moonshot.ai/v1").rstrip("/")
        self.kimi_model = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

    def decide_provider(
        self,
        *,
        task_type: str,
        prompt: str,
        priority: str,
        force_provider: str | None,
    ) -> RouteDecision:
        if force_provider in {"ollama", "kimi"}:
            forced_model = self.kimi_model if force_provider == "kimi" else self.ollama_chat_model
            return RouteDecision(provider=force_provider, model=forced_model, reason="forced_by_request")

        lowered_prompt = prompt.lower()
        todo_keywords = {"todo", "to-do", "task list", "чеклист", "список задач", "заметк", "note"}
        hard_kimi_keywords = {
            "research",
            "benchmark",
            "конкурент",
            "рынок",
            "deep analysis",
            "long context",
            "strategy",
            "аналит",
            "комплаенс",
            "регулятор",
            "презентац",
            "analytics",
            "data analysis",
            "deep dive",
        }
        if task_type in {"analysis", "report", "presentation", "data_analysis"} and priority == "high":
            return RouteDecision(provider="kimi", model=self.kimi_model, reason="high_priority_advanced_analysis")
        if any(keyword in lowered_prompt for keyword in hard_kimi_keywords):
            return RouteDecision(provider="kimi", model=self.kimi_model, reason="hard_rule_keyword_match")
        if task_type in {"todo", "note"} or any(keyword in lowered_prompt for keyword in todo_keywords):
            return RouteDecision(provider="ollama", model=self.ollama_todo_model, reason="todo_or_note_flow")

        return RouteDecision(provider="ollama", model=self.ollama_chat_model, reason="default_chat_flow")

    async def run(
        self,
        *,
        task_type: str,
        prompt: str,
        context: dict | None,
        priority: str,
        force_provider: str | None,
    ) -> dict:
        route = self.decide_provider(
            task_type=task_type,
            prompt=prompt,
            priority=priority,
            force_provider=force_provider,
        )
        if route.provider == "kimi":
            kimi_result = await self._call_kimi(task_type=task_type, prompt=prompt, context=context)
            if kimi_result["status"] == "result_ready":
                return {"provider": "kimi", "model_used": route.model, "route_reason": route.reason, **kimi_result}
            # Reliability fallback: if Kimi fails, continue with local model.
            fallback_model = self.ollama_todo_model if task_type in {"todo", "note"} else self.ollama_chat_model
            local_result = await self._call_ollama(
                task_type=task_type, prompt=prompt, context=context, model=fallback_model
            )
            return {
                "provider": "ollama",
                "model_used": fallback_model,
                "route_reason": f"{route.reason}_fallback_ollama",
                "fallback_from": "kimi",
                "fallback_error": kimi_result.get("error", "unknown_error"),
                **self._merge_with_fallback_error(
                    local_result,
                    f"Kimi failed first: {kimi_result.get('error', 'unknown_error')}",
                ),
            }

        ollama_result = await self._call_ollama(
            task_type=task_type,
            prompt=prompt,
            context=context,
            model=route.model,
        )
        return {"provider": "ollama", "model_used": route.model, "route_reason": route.reason, **ollama_result}

    async def _call_ollama(self, *, task_type: str, prompt: str, context: dict | None, model: str) -> dict:
        system_prompt = self._ollama_system_prompt(task_type)
        user_payload = {
            "task_type": task_type,
            "prompt": prompt,
            "context": context or {},
            "required_schema": {
                "summary": "string",
                "steps": ["string"],
                "risks": ["string"],
                "report_markdown": "string",
            },
        }
        body = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "options": {"temperature": 0.2},
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.ollama_base_url}/api/chat", json=body)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return self._error_result(f"Ollama request failed: {exc!s}")

        content = (((data.get("message") or {}).get("content")) or "").strip()
        parsed = self._safe_json(content)
        if not isinstance(parsed, dict):
            parsed = {
                "summary": "Local model returned unstructured output.",
                "steps": ["Inspect raw output in artifacts."],
                "risks": ["Response was not valid JSON."],
                "report_markdown": content or "No response text.",
            }

        return {
            "status": "result_ready",
            "result": parsed,
            "artifacts": [
                {"type": "report_markdown", "content": parsed.get("report_markdown", "")},
                {"type": "task_graph", "content": {"steps": parsed.get("steps", [])}},
            ],
        }

    async def _call_kimi(self, *, task_type: str, prompt: str, context: dict | None) -> dict:
        if not self.kimi_api_key:
            return self._error_result("KIMI_API_KEY is not configured.")

        system_prompt = (
            "You are a senior analyst agent. "
            "Return ONLY valid JSON with fields: summary, steps, risks, report_markdown. "
            "Use clear business language and prioritize decision-ready output."
        )
        user_payload = {
            "task_type": task_type,
            "prompt": prompt,
            "context": context or {},
            "required_schema": {
                "summary": "string",
                "steps": ["string"],
                "risks": ["string"],
                "report_markdown": "string",
            },
        }
        headers = {
            "Authorization": f"Bearer {self.kimi_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.kimi_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.kimi_api_base_url}/chat/completions",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            return self._error_result(f"Kimi request failed: {exc!s}")

        message = ((((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or "").strip()
        parsed = self._safe_json(message)
        if not isinstance(parsed, dict):
            parsed = {
                "summary": "Kimi returned unstructured output.",
                "steps": ["Inspect raw output in artifacts."],
                "risks": ["Response was not valid JSON."],
                "report_markdown": message or "No response text.",
            }

        return {
            "status": "result_ready",
            "result": parsed,
            "artifacts": [
                {"type": "report_markdown", "content": parsed.get("report_markdown", "")},
                {"type": "task_graph", "content": {"steps": parsed.get("steps", [])}},
            ],
        }

    def _safe_json(self, content: str) -> dict | list | None:
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _ollama_system_prompt(self, task_type: str) -> str:
        if task_type in {"todo", "note"}:
            return (
                "You are a concise productivity assistant. Return ONLY valid JSON with fields: "
                "summary, steps, risks, report_markdown. "
                "For todo and notes, keep steps short and ordered."
            )
        return (
            "You are a user-facing conversation and planning assistant. Return ONLY valid JSON with fields: "
            "summary, steps, risks, report_markdown. "
            "Keep output practical and easy to execute."
        )

    def _error_result(self, error: str) -> dict:
        return {
            "status": "error",
            "error": error,
            "result": {
                "summary": "The requested AI provider is unavailable.",
                "steps": ["Check provider credentials, model availability, and network access."],
                "risks": [error],
                "report_markdown": f"Provider error: {error}",
            },
            "artifacts": [
                {"type": "report_markdown", "content": f"Provider error: {error}"},
                {"type": "task_graph", "content": {"steps": []}},
            ],
        }

    def _merge_with_fallback_error(self, result: dict, fallback_message: str) -> dict:
        if result.get("status") == "result_ready":
            return result

        merged = dict(result)
        merged_result = dict(merged.get("result") or {})
        merged_result.setdefault("summary", "Primary and fallback AI providers are unavailable.")
        merged_result["risks"] = [fallback_message, *list(merged_result.get("risks") or [])]
        merged["result"] = merged_result
        return merged

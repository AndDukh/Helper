import json
import os
from collections.abc import Generator
from typing import Any

import requests


class LLMService:
    """LLM service backed by a locally-running Ollama instance.

    Environment variables
    ---------------------
    OLLAMA_API_BASE : str
        Base URL of the Ollama HTTP API (default: ``http://ollama:11434``).
    LLM_MODEL : str
        Model tag to use for generation (default: ``mistral``).
    """

    def __init__(self) -> None:
        self.api_base = os.getenv("OLLAMA_API_BASE", "http://ollama:11434").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "mistral").strip() or "mistral"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat request to Ollama and return the full response dict.

        Parameters
        ----------
        messages:
            OpenAI-style message list, e.g.
            ``[{"role": "user", "content": "Hello"}]``.
        model:
            Override the default model for this call.
        temperature:
            Sampling temperature (0 = deterministic, 1 = creative).
        stream:
            When *True* the raw streamed text is collected and returned
            under the ``content`` key so callers get a single dict
            regardless of streaming mode.

        Returns
        -------
        dict with keys:
            ``provider``, ``model``, ``content``, ``status``
        """
        target_model = (model or self.model).strip() or "mistral"

        if stream:
            content = "".join(self._stream_chat(messages, target_model, temperature))
            return {
                "provider": "ollama",
                "model": target_model,
                "content": content,
                "status": "result_ready",
            }

        return self._chat_blocking(messages, target_model, temperature)

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a plain-text generation request to Ollama.

        Parameters
        ----------
        prompt:
            Raw prompt string.
        model:
            Override the default model for this call.
        temperature:
            Sampling temperature.
        stream:
            When *True* the streamed tokens are collected before returning.

        Returns
        -------
        dict with keys:
            ``provider``, ``model``, ``content``, ``status``
        """
        target_model = (model or self.model).strip() or "mistral"

        if stream:
            content = "".join(self._stream_generate(prompt, target_model, temperature))
            return {
                "provider": "ollama",
                "model": target_model,
                "content": content,
                "status": "result_ready",
            }

        return self._generate_blocking(prompt, target_model, temperature)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """Yield text tokens from a streaming chat request.

        Suitable for FastAPI ``StreamingResponse`` endpoints.
        """
        target_model = (model or self.model).strip() or "mistral"
        yield from self._stream_chat(messages, target_model, temperature)

    def stream_generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """Yield text tokens from a streaming generate request.

        Suitable for FastAPI ``StreamingResponse`` endpoints.
        """
        target_model = (model or self.model).strip() or "mistral"
        yield from self._stream_generate(prompt, target_model, temperature)

    def health_check(self) -> dict[str, Any]:
        """Return a dict describing Ollama reachability and available models."""
        try:
            resp = requests.get(f"{self.api_base}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name") for m in (data.get("models") or [])]
            return {"status": "ok", "api_base": self.api_base, "available_models": models}
        except requests.exceptions.ConnectionError:
            return {
                "status": "unreachable",
                "api_base": self.api_base,
                "detail": "Cannot connect to Ollama. Is the service running?",
            }
        except requests.exceptions.HTTPError as exc:
            return {"status": "error", "api_base": self.api_base, "detail": str(exc)}

    # ------------------------------------------------------------------
    # Private helpers — blocking
    # ------------------------------------------------------------------

    def _chat_blocking(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = requests.post(
                f"{self.api_base}/api/chat",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            return self._connection_error(model, exc)
        except requests.exceptions.HTTPError as exc:
            return self._http_error(model, exc)

        data = resp.json()
        content = ((data.get("message") or {}).get("content") or "").strip()
        return {
            "provider": "ollama",
            "model": model,
            "content": content or "(empty response)",
            "status": "result_ready",
        }

    def _generate_blocking(
        self,
        prompt: str,
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = requests.post(
                f"{self.api_base}/api/generate",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            return self._connection_error(model, exc)
        except requests.exceptions.HTTPError as exc:
            return self._http_error(model, exc)

        data = resp.json()
        content = (data.get("response") or "").strip()
        return {
            "provider": "ollama",
            "model": model,
            "content": content or "(empty response)",
            "status": "result_ready",
        }

    # ------------------------------------------------------------------
    # Private helpers — streaming
    # ------------------------------------------------------------------

    def _stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            with requests.post(
                f"{self.api_base}/api/chat",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    chunk = json.loads(raw_line)
                    token = ((chunk.get("message") or {}).get("content") or "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except requests.exceptions.ConnectionError as exc:
            yield f"[LLMService error] Cannot connect to Ollama at {self.api_base}: {exc}"
        except requests.exceptions.HTTPError as exc:
            yield f"[LLMService error] Ollama HTTP error: {exc}"

    def _stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
    ) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            with requests.post(
                f"{self.api_base}/api/generate",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    chunk = json.loads(raw_line)
                    token = (chunk.get("response") or "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except requests.exceptions.ConnectionError as exc:
            yield f"[LLMService error] Cannot connect to Ollama at {self.api_base}: {exc}"
        except requests.exceptions.HTTPError as exc:
            yield f"[LLMService error] Ollama HTTP error: {exc}"

    # ------------------------------------------------------------------
    # Private helpers — error formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _connection_error(model: str, exc: Exception) -> dict[str, Any]:
        return {
            "provider": "ollama",
            "model": model,
            "content": "",
            "status": "error",
            "detail": f"Cannot connect to Ollama: {exc}",
        }

    @staticmethod
    def _http_error(model: str, exc: Exception) -> dict[str, Any]:
        return {
            "provider": "ollama",
            "model": model,
            "content": "",
            "status": "error",
            "detail": f"Ollama HTTP error: {exc}",
        }

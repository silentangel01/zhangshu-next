"""DashScope cloud LLM provider using httpx.

Calls Alibaba Cloud DashScope (Bailian) chat completions via the
OpenAI-compatible HTTP API.  Does NOT import any Alibaba SDK.

Sensitive data (API key, prompts, context, responses) is never
written to logs.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# DashScope chat API defaults
DEFAULT_LLM_MODEL = "qwen-plus"
DEFAULT_LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_TIMEOUT = 60.0
MAX_CONTEXT_CHARS = 8000
MAX_RESPONSE_TOKENS = 1024


# --- Exceptions ---


class DashScopeLLMError(Exception):
    """Raised when a DashScope LLM API call fails."""


class DashScopeLLMAuthError(DashScopeLLMError):
    """Raised when authentication fails (401/403)."""


# --- Provider ---


class DashScopeLLMProvider:
    """Cloud LLM provider backed by DashScope chat completions.

    Implements the ``LLMProvider`` Protocol defined in
    ``app.infrastructure.llm_provider``.
    """

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise DashScopeLLMAuthError("DashScope API key is required.")

        self._api_key = api_key
        self._model = model or DEFAULT_LLM_MODEL
        self._base_url = (base_url or DEFAULT_LLM_BASE_URL).rstrip("/")
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT)

    # --- LLMProvider Protocol ---

    def generate(self, prompt: str, context: str) -> str:
        """Generate a response based on a question and retrieved context."""
        system_msg = (
            "你是章枢写作助手的知识库问答模块。"
            "请根据以下知识库内容回答用户的问题。"
            "如果知识库内容不足以回答问题，请如实说明。"
            "回答应简洁、准确，使用中文。"
        )

        # Truncate context to avoid token limits
        ctx = context.strip()
        if len(ctx) > MAX_CONTEXT_CHARS:
            ctx = ctx[:MAX_CONTEXT_CHARS] + "\n\n[内容已截断]"

        user_msg = f"知识库内容：\n{ctx}\n\n问题：{prompt}" if ctx else prompt

        return self._chat(system_msg, user_msg)

    def summarize(self, texts: list[str], instruction: str) -> str:
        """Generate a summary of multiple text segments."""
        system_msg = (
            "你是章枢写作助手的知识库摘要模块。"
            "请根据指令对以下知识库内容进行摘要。"
            "摘要应结构清晰、重点突出，使用中文。"
        )

        # Build combined text with truncation
        parts: list[str] = []
        total_len = 0
        for i, text in enumerate(texts, 1):
            segment = f"[{i}] {text}"
            if total_len + len(segment) > MAX_CONTEXT_CHARS:
                remaining = MAX_CONTEXT_CHARS - total_len
                if remaining > 100:
                    parts.append(segment[:remaining] + "...")
                break
            parts.append(segment)
            total_len += len(segment)

        combined = "\n".join(parts)
        user_msg = f"{instruction}\n\n{combined}"

        return self._chat(system_msg, user_msg)

    @property
    def model_name(self) -> str:
        return self._model

    # --- Internal ---

    def _chat(self, system_msg: str, user_msg: str) -> str:
        """Send a chat completion request to DashScope.

        Raises ``DashScopeLLMError`` on any failure.
        """
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": MAX_RESPONSE_TOKENS,
            "temperature": 0.3,
        }

        try:
            response = self._client.post(url, headers=headers, json=body)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("DashScope LLM request timed out.")
            raise DashScopeLLMError("AI 问答请求超时，请稍后重试。") from exc
        except httpx.ConnectError as exc:
            logger.warning("DashScope LLM connection failed.")
            raise DashScopeLLMError(
                "无法连接 AI 问答服务，请检查网络。"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("DashScope LLM API returned HTTP %d.", status)
            if status in (401, 403):
                raise DashScopeLLMAuthError(
                    "AI 问答认证失败，请检查 API Key。"
                ) from exc
            if status == 429:
                raise DashScopeLLMError(
                    "AI 问答请求过于频繁，请稍后重试。"
                ) from exc
            raise DashScopeLLMError(
                f"AI 问答服务返回错误（HTTP {status}）。"
            ) from exc

        # Parse response
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return str(content).strip()
        except (KeyError, TypeError, IndexError, ValueError) as exc:
            logger.warning("DashScope LLM response parse error.")
            raise DashScopeLLMError(
                "AI 问答响应格式异常，无法解析。"
            ) from exc

"""DashScope cloud embedding provider using httpx.

Calls Alibaba Cloud DashScope (Bailian) text-embedding-v4 via the
OpenAI-compatible HTTP API.  Does NOT import any Alibaba SDK.

Sensitive data (API key, request body text, response vectors) is
never written to logs.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.infrastructure.embedding_settings import (
    get_dashscope_base_url,
    get_dashscope_dim,
    get_dashscope_model,
)

logger = logging.getLogger(__name__)

# DashScope API limits
MAX_BATCH_SIZE = 25
DEFAULT_TIMEOUT = 30.0


# --- Exceptions ---


class DashScopeEmbeddingError(Exception):
    """Raised when a DashScope API call fails (network, HTTP, or parse error)."""


class DashScopeApiKeyMissingError(Exception):
    """Raised when the DashScope API key is not configured."""


# --- Provider ---


class DashScopeEmbeddingProvider:
    """Cloud embedding provider backed by DashScope text-embedding-v4.

    Implements the ``EmbeddingProvider`` Protocol defined in
    ``app.infrastructure.embedding_provider``.
    """

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        vector_dim: int | None = None,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise DashScopeApiKeyMissingError("DashScope API key is required.")

        self._api_key = api_key
        self._model = model or get_dashscope_model()
        self._vector_dim = vector_dim or get_dashscope_dim()
        self._base_url = (base_url or get_dashscope_base_url()).rstrip("/")
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT)

    # --- EmbeddingProvider Protocol ---

    def encode(self, text: str) -> list[float]:
        """Encode a single text into an embedding vector."""
        if not text or not text.strip():
            return [0.0] * self._vector_dim
        results = self._call_api([text])
        return results[0]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts, auto-splitting into batches of MAX_BATCH_SIZE."""
        if not texts:
            return []

        all_results: list[list[float]] = []
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            # Replace empty strings with a placeholder to avoid API errors
            sanitized = [t if t and t.strip() else " " for t in batch]
            batch_results = self._call_api(sanitized)
            # Restore zero vectors for originally empty inputs
            for j, original in enumerate(batch):
                if not original or not original.strip():
                    batch_results[j] = [0.0] * self._vector_dim
            all_results.extend(batch_results)

        return all_results

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def vector_dim(self) -> int:
        return self._vector_dim

    # --- Internal ---

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """POST to DashScope OpenAI-compatible embedding endpoint.

        Raises ``DashScopeEmbeddingError`` on any failure.
        """
        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "input": texts,
            "dimensions": self._vector_dim,
        }

        try:
            response = self._client.post(url, headers=headers, json=body)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("DashScope embedding request timed out.")
            raise DashScopeEmbeddingError("云端 Embedding 请求超时，请稍后重试。") from exc
        except httpx.ConnectError as exc:
            logger.warning("DashScope connection failed.")
            raise DashScopeEmbeddingError("无法连接云端 Embedding 服务，请检查网络。") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning("DashScope API returned HTTP %d.", status)
            if status in (401, 403):
                raise DashScopeEmbeddingError(
                    "云端 Embedding 认证失败，请检查 API Key。"
                ) from exc
            if status == 429:
                raise DashScopeEmbeddingError(
                    "云端 Embedding 请求过于频繁，请稍后重试。"
                ) from exc
            raise DashScopeEmbeddingError(
                f"云端 Embedding 服务返回错误（HTTP {status}）。"
            ) from exc

        # Parse response
        try:
            data = response.json()
            items = data["data"]
            # Sort by index to preserve input order
            sorted_items = sorted(items, key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_items]
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("DashScope response parse error.")
            raise DashScopeEmbeddingError(
                "云端 Embedding 响应格式异常，无法解析。"
            ) from exc

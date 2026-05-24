"""LLM provider factory — creates Stub or DashScope provider based on config.

Decision chain:
  llm_enabled != "true" → StubLLMProvider
  no dashscope_api_key  → StubLLMProvider
  otherwise             → DashScopeLLMProvider
"""

from __future__ import annotations

import logging

from app.infrastructure.dashscope_llm_provider import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DashScopeLLMProvider,
)
from app.infrastructure.llm_provider import LLMProvider, StubLLMProvider
from app.services.app_config_service import (
    KEY_DASHSCOPE_API_KEY,
    AppConfigService,
)

logger = logging.getLogger(__name__)

# App config keys for LLM settings
KEY_LLM_ENABLED = "llm_enabled"
KEY_LLM_MODEL = "llm_model"
KEY_LLM_BASE_URL = "llm_base_url"
KEY_LLM_PROVIDER = "llm_provider"


class LLMProviderFactory:
    """Creates an LLMProvider based on app configuration."""

    def __init__(self, config_service: AppConfigService):
        self._config = config_service

    def create(self) -> LLMProvider:
        """Return the configured LLM provider.

        Falls back to StubLLMProvider if cloud LLM is not enabled
        or the API key is missing.
        """
        enabled = self._config.get_value(KEY_LLM_ENABLED)
        if enabled != "true":
            return StubLLMProvider()

        api_key = self._config.get_decrypted(KEY_DASHSCOPE_API_KEY)
        if not api_key or not api_key.strip():
            logger.info("LLM enabled but no API key configured, using stub.")
            return StubLLMProvider()

        model = self._config.get_value(KEY_LLM_MODEL) or DEFAULT_LLM_MODEL
        base_url = (
            self._config.get_value(KEY_LLM_BASE_URL) or DEFAULT_LLM_BASE_URL
        )

        return DashScopeLLMProvider(
            api_key=api_key.strip(),
            model=model.strip(),
            base_url=base_url.strip(),
        )

    def is_cloud_llm_enabled(self) -> bool:
        """Return True if cloud LLM is enabled and configured."""
        enabled = self._config.get_value(KEY_LLM_ENABLED)
        if enabled != "true":
            return False
        api_key = self._config.get_decrypted(KEY_DASHSCOPE_API_KEY)
        return bool(api_key and api_key.strip())

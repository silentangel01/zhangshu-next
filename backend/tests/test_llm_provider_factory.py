"""Tests for LLMProviderFactory — stub vs. real provider decision chain."""

import pytest

from app.infrastructure.llm_provider import LLMProvider, StubLLMProvider
from app.infrastructure.llm_provider_factory import LLMProviderFactory
from app.services.app_config_service import (
    KEY_DASHSCOPE_API_KEY,
    KEY_LLM_BASE_URL,
    KEY_LLM_ENABLED,
    KEY_LLM_MODEL,
)


class FakeConfigService:
    """Minimal mock of AppConfigService for factory tests."""

    def __init__(self, values: dict[str, str | None] | None = None):
        self._values = values or {}

    def get_value(self, key: str) -> str | None:
        return self._values.get(key)

    def get_decrypted(self, key: str) -> str | None:
        return self._values.get(key)


class TestCreateStubProvider:
    def test_llm_not_enabled_returns_stub(self):
        config = FakeConfigService({KEY_LLM_ENABLED: "false"})
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert isinstance(provider, StubLLMProvider)

    def test_llm_enabled_not_set_returns_stub(self):
        config = FakeConfigService({})
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert isinstance(provider, StubLLMProvider)

    def test_llm_enabled_but_no_key_returns_stub(self):
        config = FakeConfigService({KEY_LLM_ENABLED: "true"})
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert isinstance(provider, StubLLMProvider)

    def test_llm_enabled_empty_key_returns_stub(self):
        config = FakeConfigService({
            KEY_LLM_ENABLED: "true",
            KEY_DASHSCOPE_API_KEY: "   ",
        })
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert isinstance(provider, StubLLMProvider)


class TestCreateRealProvider:
    def test_llm_enabled_with_key_returns_dashscope(self):
        config = FakeConfigService({
            KEY_LLM_ENABLED: "true",
            KEY_DASHSCOPE_API_KEY: "sk-test-key-12345",
        })
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert isinstance(provider, LLMProvider)
        assert not isinstance(provider, StubLLMProvider)
        assert provider.model_name == "qwen-plus"  # default model

    def test_custom_model_passed(self):
        config = FakeConfigService({
            KEY_LLM_ENABLED: "true",
            KEY_DASHSCOPE_API_KEY: "sk-test-key-12345",
            KEY_LLM_MODEL: "qwen-max",
        })
        factory = LLMProviderFactory(config)
        provider = factory.create()
        assert provider.model_name == "qwen-max"

    def test_custom_base_url_passed(self):
        config = FakeConfigService({
            KEY_LLM_ENABLED: "true",
            KEY_DASHSCOPE_API_KEY: "sk-test-key-12345",
            KEY_LLM_BASE_URL: "https://custom-api.example.com/v1",
        })
        factory = LLMProviderFactory(config)
        provider = factory.create()
        # Can't easily verify base_url without exposing it,
        # but provider should be created successfully
        assert not isinstance(provider, StubLLMProvider)


class TestIsCloudLlmEnabled:
    def test_disabled_when_not_enabled(self):
        config = FakeConfigService({KEY_LLM_ENABLED: "false"})
        factory = LLMProviderFactory(config)
        assert factory.is_cloud_llm_enabled() is False

    def test_disabled_when_no_key(self):
        config = FakeConfigService({KEY_LLM_ENABLED: "true"})
        factory = LLMProviderFactory(config)
        assert factory.is_cloud_llm_enabled() is False

    def test_enabled_when_both_set(self):
        config = FakeConfigService({
            KEY_LLM_ENABLED: "true",
            KEY_DASHSCOPE_API_KEY: "sk-test-key",
        })
        factory = LLMProviderFactory(config)
        assert factory.is_cloud_llm_enabled() is True

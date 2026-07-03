"""Tests for the embedding provider factory."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.embedding_provider import BigramHashEmbeddingProvider  # noqa: E402
from app.infrastructure.embedding_provider_factory import (  # noqa: E402
    PROVIDER_DASHSCOPE_V4,
    PROVIDER_LOCAL_BASIC_HASH,
    PROVIDER_LOCAL_BGE_M3,
    PROVIDER_LOCAL_BGE_SMALL_ZH,
    create_provider,
    get_default_provider,
    get_default_provider_id,
    get_provider_descriptor,
    list_provider_options,
)
from app.infrastructure.dashscope_embedding_provider import (  # noqa: E402
    DashScopeApiKeyMissingError,
    DashScopeEmbeddingProvider,
)


class TestListProviders:
    def test_list_returns_four_providers(self):
        providers = list_provider_options()
        assert len(providers) == 4

    def test_all_provider_ids_present(self):
        providers = list_provider_options()
        ids = {p.id for p in providers}
        assert PROVIDER_LOCAL_BASIC_HASH in ids
        assert PROVIDER_LOCAL_BGE_SMALL_ZH in ids
        assert PROVIDER_LOCAL_BGE_M3 in ids
        assert PROVIDER_DASHSCOPE_V4 in ids

    def test_basic_hash_always_available(self):
        providers = list_provider_options()
        basic = next(p for p in providers if p.id == PROVIDER_LOCAL_BASIC_HASH)
        assert basic.available is True
        assert basic.provider_type == "compat"
        assert basic.requires_privacy_confirm is False

    def test_bge_small_zh_unavailable(self):
        providers = list_provider_options()
        bge = next(p for p in providers if p.id == PROVIDER_LOCAL_BGE_SMALL_ZH)
        assert bge.available is False
        assert bge.reason != ""

    def test_bge_m3_unavailable(self):
        providers = list_provider_options()
        bge = next(p for p in providers if p.id == PROVIDER_LOCAL_BGE_M3)
        assert bge.available is False
        assert bge.reason != ""

    def test_dashscope_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("ZHANGSHU_DASHSCOPE_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.infrastructure.embedding_settings._get_api_key_from_db",
            lambda: None,
        )
        providers = list_provider_options()
        ds = next(p for p in providers if p.id == PROVIDER_DASHSCOPE_V4)
        assert ds.available is False
        assert ds.requires_privacy_confirm is True
        assert ds.provider_type == "cloud"

    def test_dashscope_available_with_key(self, monkeypatch):
        monkeypatch.setenv("ZHANGSHU_DASHSCOPE_API_KEY", "test-key-123")
        providers = list_provider_options()
        ds = next(p for p in providers if p.id == PROVIDER_DASHSCOPE_V4)
        assert ds.available is True


class TestGetDescriptor:
    def test_known_id(self):
        desc = get_provider_descriptor(PROVIDER_LOCAL_BASIC_HASH)
        assert desc.id == PROVIDER_LOCAL_BASIC_HASH
        assert desc.model_name == "bigram-hash-v2"
        assert desc.vector_dim == 256

    def test_unknown_id_raises(self):
        with pytest.raises(ValueError, match="未知"):
            get_provider_descriptor("nonexistent_provider")


class TestCreateProvider:
    def test_create_basic_hash(self):
        provider = create_provider(PROVIDER_LOCAL_BASIC_HASH)
        assert isinstance(provider, BigramHashEmbeddingProvider)
        assert provider.model_name == "bigram-hash-v2"

    def test_create_unavailable_raises(self):
        with pytest.raises(RuntimeError, match="不可用"):
            create_provider(PROVIDER_LOCAL_BGE_SMALL_ZH)

    def test_create_dashscope_without_key_raises(self, monkeypatch):
        monkeypatch.delenv("ZHANGSHU_DASHSCOPE_API_KEY", raising=False)
        monkeypatch.setattr(
            "app.infrastructure.embedding_settings._get_api_key_from_db",
            lambda: None,
        )
        with pytest.raises(RuntimeError, match="不可用"):
            create_provider(PROVIDER_DASHSCOPE_V4)

    def test_create_dashscope_with_key(self, monkeypatch):
        monkeypatch.setenv("ZHANGSHU_DASHSCOPE_API_KEY", "test-key-123")
        provider = create_provider(PROVIDER_DASHSCOPE_V4)
        assert isinstance(provider, DashScopeEmbeddingProvider)

    def test_unknown_id_raises(self):
        with pytest.raises(ValueError):
            create_provider("nonexistent_provider")


class TestDefaultProvider:
    def test_default_provider_id(self):
        assert get_default_provider_id() == PROVIDER_LOCAL_BASIC_HASH

    def test_default_provider_instance(self):
        provider = get_default_provider()
        assert isinstance(provider, BigramHashEmbeddingProvider)

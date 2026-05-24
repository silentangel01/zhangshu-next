"""Embedding provider factory.

Centralises provider creation, availability checks, and listing.
API, Service, and UI layers should use this factory instead of
importing concrete provider classes directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.infrastructure.dashscope_embedding_provider import (
    DashScopeApiKeyMissingError,
    DashScopeEmbeddingProvider,
)
from app.infrastructure.embedding_provider import (
    BigramHashEmbeddingProvider,
    EmbeddingProvider,
)
from app.infrastructure.embedding_settings import (
    get_dashscope_api_key,
    get_dashscope_dim,
    get_dashscope_model,
    is_cloud_embedding_available,
)

ProviderType = Literal["local", "cloud", "compat"]

# --- Provider IDs ---

PROVIDER_LOCAL_BASIC_HASH = "local_basic_hash"
PROVIDER_LOCAL_BGE_SMALL_ZH = "local_bge_small_zh"
PROVIDER_LOCAL_BGE_M3 = "local_bge_m3"
PROVIDER_DASHSCOPE_V4 = "dashscope_text_embedding_v4"

_ALL_PROVIDER_IDS = [
    PROVIDER_LOCAL_BASIC_HASH,
    PROVIDER_LOCAL_BGE_SMALL_ZH,
    PROVIDER_LOCAL_BGE_M3,
    PROVIDER_DASHSCOPE_V4,
]


# --- Descriptor ---


@dataclass(frozen=True)
class ProviderDescriptor:
    """Static metadata describing a known embedding provider."""

    id: str
    display_name: str
    provider_type: ProviderType
    model_name: str
    vector_dim: int
    available: bool
    reason: str
    requires_privacy_confirm: bool
    requires_network: bool
    quality_label: str
    description: str


# --- Public API ---


def list_provider_options() -> list[ProviderDescriptor]:
    """Return all known providers with current availability status."""
    return [_describe(pid) for pid in _ALL_PROVIDER_IDS]


def get_provider_descriptor(provider_id: str) -> ProviderDescriptor:
    """Return descriptor for a known provider ID.

    Raises ``ValueError`` if the ID is unknown.
    """
    if provider_id not in _ALL_PROVIDER_IDS:
        raise ValueError(f"未知的 Embedding Provider：{provider_id}")
    return _describe(provider_id)


def create_provider(provider_id: str) -> EmbeddingProvider:
    """Create and return a provider instance.

    Raises:
        ValueError: Unknown provider ID.
        RuntimeError: Provider is not available (missing key, model file, etc.).
        DashScopeApiKeyMissingError: Cloud provider key not configured.
    """
    descriptor = get_provider_descriptor(provider_id)

    if not descriptor.available:
        raise RuntimeError(
            f"Provider '{provider_id}' 不可用：{descriptor.reason}"
        )

    if provider_id == PROVIDER_LOCAL_BASIC_HASH:
        return BigramHashEmbeddingProvider()

    if provider_id == PROVIDER_DASHSCOPE_V4:
        api_key = get_dashscope_api_key()
        if api_key is None:
            raise DashScopeApiKeyMissingError(
                "DashScope API Key 未配置。请在应用设置中填写 Key，"
                "或设置环境变量 ZHANGSHU_DASHSCOPE_API_KEY。"
            )
        return DashScopeEmbeddingProvider(api_key=api_key)

    # Placeholder providers — should never reach here because available=False
    raise RuntimeError(
        f"Provider '{provider_id}' 尚未实现。{descriptor.reason}"
    )


def get_default_provider() -> EmbeddingProvider:
    """Return the default (always-available) provider."""
    return BigramHashEmbeddingProvider()


def get_default_provider_id() -> str:
    """Return the default provider ID."""
    return PROVIDER_LOCAL_BASIC_HASH


# --- Internal ---


def _describe(provider_id: str) -> ProviderDescriptor:
    """Build a descriptor for a known provider with current availability."""

    if provider_id == PROVIDER_LOCAL_BASIC_HASH:
        return ProviderDescriptor(
            id=PROVIDER_LOCAL_BASIC_HASH,
            display_name="本地基础索引",
            provider_type="compat",
            model_name=BigramHashEmbeddingProvider.MODEL_NAME,
            vector_dim=BigramHashEmbeddingProvider.VECTOR_DIM,
            available=True,
            reason="",
            requires_privacy_confirm=False,
            requires_network=False,
            quality_label="基础",
            description="离线可用，不上传资料。基于字符哈希的兼容索引，检索质量较基础。",
        )

    if provider_id == PROVIDER_LOCAL_BGE_SMALL_ZH:
        return ProviderDescriptor(
            id=PROVIDER_LOCAL_BGE_SMALL_ZH,
            display_name="本地轻量索引",
            provider_type="local",
            model_name="bge-small-zh-v1.5",
            vector_dim=512,
            available=False,
            reason="本地模型文件尚未安装，当前版本暂不支持此模式。",
            requires_privacy_confirm=False,
            requires_network=False,
            quality_label="良好",
            description="离线可用，不上传资料。需要安装本地模型文件后使用。",
        )

    if provider_id == PROVIDER_LOCAL_BGE_M3:
        return ProviderDescriptor(
            id=PROVIDER_LOCAL_BGE_M3,
            display_name="本地高质量索引",
            provider_type="local",
            model_name="bge-m3",
            vector_dim=1024,
            available=False,
            reason="本地模型文件尚未安装，当前版本暂不支持此模式。",
            requires_privacy_confirm=False,
            requires_network=False,
            quality_label="优秀",
            description="离线可用，不上传资料。需要安装较大的本地模型文件。",
        )

    if provider_id == PROVIDER_DASHSCOPE_V4:
        cloud_available = is_cloud_embedding_available()
        reason = "" if cloud_available else "需要在应用设置中填写 DashScope API Key，或设置环境变量 ZHANGSHU_DASHSCOPE_API_KEY。"
        return ProviderDescriptor(
            id=PROVIDER_DASHSCOPE_V4,
            display_name="云端精准索引",
            provider_type="cloud",
            model_name=get_dashscope_model(),
            vector_dim=get_dashscope_dim(),
            available=cloud_available,
            reason=reason,
            requires_privacy_confirm=True,
            requires_network=True,
            quality_label="精准",
            description="联网生成更精准的语义索引。资料片段会发送到阿里云百炼服务。",
        )

    # Should never happen — guard against _ALL_PROVIDER_IDS drift
    raise ValueError(f"未知的 Embedding Provider：{provider_id}")

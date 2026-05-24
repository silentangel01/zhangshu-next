"""Embedding provider environment configuration.

Reads embedding-related settings from environment variables.
Never logs or prints API keys or secrets.
"""

import os

# Environment variable names
ENV_DASHSCOPE_API_KEY = "ZHANGSHU_DASHSCOPE_API_KEY"
ENV_DASHSCOPE_EMBEDDING_MODEL = "ZHANGSHU_DASHSCOPE_EMBEDDING_MODEL"
ENV_DASHSCOPE_EMBEDDING_DIM = "ZHANGSHU_DASHSCOPE_EMBEDDING_DIM"
ENV_DASHSCOPE_BASE_URL = "ZHANGSHU_DASHSCOPE_BASE_URL"

# Defaults
DEFAULT_DASHSCOPE_MODEL = "text-embedding-v4"
DEFAULT_DASHSCOPE_DIM = 1024
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _get_api_key_from_db() -> str | None:
    """Read DashScope API key from app_config DB (encrypted).

    Uses deferred imports to avoid circular dependencies at module load time.
    Returns decrypted plaintext or None.
    """
    try:
        from app.infrastructure.database import SessionLocal
        from app.services.app_config_service import (
            AppConfigService,
            KEY_DASHSCOPE_API_KEY,
        )
    except Exception:
        return None

    db = SessionLocal()
    try:
        service = AppConfigService(db)
        return service.get_decrypted(KEY_DASHSCOPE_API_KEY)
    except Exception:
        return None
    finally:
        db.close()


def get_dashscope_api_key() -> str | None:
    """Return DashScope API key.

    Lookup order: environment variable → encrypted DB store → None.
    """
    key = os.environ.get(ENV_DASHSCOPE_API_KEY, "").strip()
    if key:
        return key
    return _get_api_key_from_db()


def is_cloud_embedding_available() -> bool:
    """Return True if DashScope API key is configured."""
    return get_dashscope_api_key() is not None


def get_dashscope_model() -> str:
    """Return the configured DashScope embedding model name."""
    return os.environ.get(ENV_DASHSCOPE_EMBEDDING_MODEL, DEFAULT_DASHSCOPE_MODEL).strip()


def get_dashscope_dim() -> int:
    """Return the configured DashScope embedding dimension."""
    raw = os.environ.get(ENV_DASHSCOPE_EMBEDDING_DIM, "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return DEFAULT_DASHSCOPE_DIM


def get_dashscope_base_url() -> str:
    """Return the configured DashScope API base URL."""
    url = os.environ.get(ENV_DASHSCOPE_BASE_URL, "").strip()
    return url if url else DEFAULT_DASHSCOPE_BASE_URL

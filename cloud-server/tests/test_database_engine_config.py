"""Tests for database engine configuration and production config validation.

Covers:
- SQLite engine does not use PostgreSQL-specific connect args
- PostgreSQL engine sets pool size, overflow, connect_timeout, statement_timeout
- Production config rejects SQLite, enforces Redis, and validates pool params
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestBuildEngineKwargs:
    """Verify _build_engine_kwargs selects the right arguments per dialect."""

    def test_sqlite_uses_check_same_thread(self):
        from app.core.config import Settings
        from app.db.session import _build_engine_kwargs

        s = Settings(
            database_url="sqlite:///./test.db",
            database_pool_size=5,
            database_max_overflow=5,
            database_pool_timeout_seconds=5,
            database_pool_recycle_seconds=1800,
            database_connect_timeout_seconds=5,
            database_statement_timeout_ms=5000,
        )
        with patch("app.db.session.settings", s):
            kwargs = _build_engine_kwargs()

        assert kwargs.get("connect_args") == {"check_same_thread": False}
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs
        assert "pool_timeout" not in kwargs

    def test_postgres_sets_pool_params(self):
        from app.core.config import Settings
        from app.db.session import _build_engine_kwargs

        s = Settings(
            database_url="postgresql://user:pass@localhost:5432/db",
            database_pool_size=7,
            database_max_overflow=3,
            database_pool_timeout_seconds=10,
            database_pool_recycle_seconds=900,
            database_connect_timeout_seconds=8,
            database_statement_timeout_ms=7000,
        )
        with patch("app.db.session.settings", s):
            kwargs = _build_engine_kwargs()

        assert kwargs["pool_size"] == 7
        assert kwargs["max_overflow"] == 3
        assert kwargs["pool_timeout"] == 10
        assert kwargs["pool_recycle"] == 900
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["connect_args"]["connect_timeout"] == 8
        assert "statement_timeout=7000" in kwargs["connect_args"]["options"]

    def test_postgres_statement_timeout_zero_omits_options(self):
        from app.core.config import Settings
        from app.db.session import _build_engine_kwargs

        s = Settings(
            database_url="postgresql://user:pass@localhost:5432/db",
            database_pool_size=5,
            database_max_overflow=5,
            database_pool_timeout_seconds=5,
            database_pool_recycle_seconds=1800,
            database_connect_timeout_seconds=5,
            database_statement_timeout_ms=0,
        )
        with patch("app.db.session.settings", s):
            kwargs = _build_engine_kwargs()

        assert "options" not in kwargs["connect_args"]


class TestValidateProductionConfig:
    """Verify validate_production_config catches bad production settings."""

    def _base_production_settings(self, **overrides):
        from app.core.config import Settings

        defaults = {
            "environment": "production",
            "jwt_secret_key": "a-very-long-random-secret-key-at-least-32",
            "admin_cookie_secure": True,
            "force_https": True,
            "admin_allow_bearer_fallback": False,
            "cors_origins": "https://example.com",
            "admin_allowed_origins": "https://admin.example.com",
            "oss_access_key_id": "AKIDTEST",
            "oss_access_key_secret": "secret",
            "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "oss_public_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            # New production-required settings
            "database_url": "postgresql://user:pass@host/db",
            "redis_enabled": True,
            "rate_limit_backend": "redis",
            "cache_backend": "redis",
            "database_pool_size": 5,
            "database_max_overflow": 5,
            "database_pool_timeout_seconds": 5,
        }
        defaults.update(overrides)
        return Settings(**defaults)

    def test_valid_production_config_passes(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings()
        issues = validate_production_config(s)
        # Filter out unrelated pre-existing issues (monitor credentials etc.)
        relevant = [
            i for i in issues
            if any(
                k in i for k in (
                    "DATABASE_URL", "REDIS_ENABLED", "RATE_LIMIT_BACKEND",
                    "CACHE_BACKEND", "DATABASE_POOL_SIZE",
                )
            )
        ]
        assert relevant == []

    def test_production_rejects_sqlite(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings(database_url="sqlite:///./prod.db")
        issues = validate_production_config(s)
        assert any("SQLite" in i for i in issues)

    def test_production_rejects_redis_disabled(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings(redis_enabled=False)
        issues = validate_production_config(s)
        assert any("REDIS_ENABLED" in i for i in issues)

    def test_production_rejects_non_redis_rate_limit(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings(rate_limit_backend="database")
        issues = validate_production_config(s)
        assert any("RATE_LIMIT_BACKEND" in i for i in issues)

    def test_production_rejects_non_redis_cache(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings(cache_backend="memory")
        issues = validate_production_config(s)
        assert any("CACHE_BACKEND" in i for i in issues)

    def test_production_rejects_zero_pool_size(self):
        from app.core.config import validate_production_config

        s = self._base_production_settings(database_pool_size=0)
        issues = validate_production_config(s)
        assert any("DATABASE_POOL_SIZE" in i for i in issues)

    def test_development_is_permissive(self):
        from app.core.config import Settings, validate_production_config

        s = Settings(environment="development")
        assert validate_production_config(s) == []

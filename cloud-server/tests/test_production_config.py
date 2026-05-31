"""Tests for production configuration validation."""

from __future__ import annotations

from app.core.config import Settings, validate_production_config


class TestValidateProductionConfig:
    def test_development_mode_returns_empty(self):
        s = Settings(environment="development")
        issues = validate_production_config(s)
        assert issues == []

    def test_production_default_jwt_secret(self):
        s = Settings(
            environment="production",
            jwt_secret_key="change-me-in-production",
        )
        issues = validate_production_config(s)
        assert any("JWT_SECRET_KEY" in i for i in issues)

    def test_production_valid_jwt_secret(self):
        s = Settings(
            environment="production",
            jwt_secret_key="a" * 64,
            cors_origins="https://example.com",
            oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            admin_allow_bearer_fallback=False,
            admin_allowed_origins="https://admin.example.com",
            database_url="postgresql://user:pass@host/db",
            redis_enabled=True,
            rate_limit_backend="redis",
            cache_backend="redis",
        )
        issues = validate_production_config(s)
        assert issues == []

    def test_production_wildcard_cors(self):
        s = Settings(
            environment="production",
            jwt_secret_key="a" * 64,
            cors_origins="*",
        )
        issues = validate_production_config(s)
        assert any("CORS" in i for i in issues)

    def test_production_internal_oss_public_endpoint(self):
        s = Settings(
            environment="production",
            jwt_secret_key="a" * 64,
            cors_origins="https://example.com",
            oss_public_endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
        )
        issues = validate_production_config(s)
        assert any("OSS_PUBLIC_ENDPOINT" in i for i in issues)

    def test_production_valid_oss_endpoint(self):
        s = Settings(
            environment="production",
            jwt_secret_key="a" * 64,
            cors_origins="https://example.com",
            oss_public_endpoint="oss-cn-hangzhou.aliyuncs.com",
            admin_allow_bearer_fallback=False,
            admin_allowed_origins="https://admin.example.com",
            database_url="postgresql://user:pass@host/db",
            redis_enabled=True,
            rate_limit_backend="redis",
            cache_backend="redis",
        )
        issues = validate_production_config(s)
        assert issues == []


class TestSettingsDefaults:
    def test_environment_default(self):
        s = Settings()
        assert s.environment == "development"

    def test_rate_limit_defaults(self):
        s = Settings()
        assert s.rate_limit_login_per_5m == 10
        assert s.rate_limit_backup_init_per_hour == 30

    def test_quota_defaults(self):
        s = Settings()
        assert s.default_storage_quota_bytes == 1_073_741_824
        assert s.default_backup_count_quota == 100

    def test_force_https_default(self):
        s = Settings()
        assert s.force_https is True

    def test_access_log_json_default(self):
        s = Settings()
        assert s.access_log_json is True

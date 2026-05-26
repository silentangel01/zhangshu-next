"""Application settings loaded from environment variables."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = "development"

    # Database
    database_url: str = "sqlite:///./cloud_server.db"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Password hashing
    bcrypt_rounds: int = 12

    # Aliyun OSS
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "zhangshu-backups"
    oss_endpoint: str = "oss-cn-hangzhou.aliyuncs.com"
    oss_public_endpoint: str = ""
    oss_internal_endpoint: str = ""
    oss_presigned_url_expire_seconds: int = 1800

    # Backup limits
    max_backup_size_bytes: int = 524_288_000  # 500 MB

    # CORS
    cors_origins: str = "http://localhost:5180,http://127.0.0.1:5180"

    # Production hardening
    force_https: bool = True
    log_level: str = "INFO"
    access_log_json: bool = True
    rate_limit_login_per_5m: int = 10
    rate_limit_backup_init_per_hour: int = 30
    default_storage_quota_bytes: int = 1_073_741_824  # 1 GB
    default_backup_count_quota: int = 100

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_public_endpoint(self) -> str:
        """Endpoint for presigned URLs (must be publicly reachable by clients)."""
        return self.oss_public_endpoint or self.oss_endpoint

    @property
    def effective_internal_endpoint(self) -> str:
        """Endpoint for server-side OSS operations (head/delete). Falls back to public."""
        return self.oss_internal_endpoint or self.effective_public_endpoint


def get_settings() -> Settings:
    return Settings()


def validate_production_config(settings: Settings) -> list[str]:
    """Validate production configuration. Returns list of issues.

    Only checks critical settings when environment=production.
    Development mode is permissive.
    """
    if settings.environment != "production":
        return []

    issues: list[str] = []

    # JWT secret must not be default
    if settings.jwt_secret_key == "change-me-in-production":
        issues.append(
            "JWT_SECRET_KEY 使用默认值，生产环境必须设置随机密钥 (≥32 字符)。"
        )

    # CORS must not be wildcard
    if "*" in settings.cors_origin_list:
        issues.append(
            "CORS_ORIGINS 不允许使用通配符 *，请指定具体域名。"
        )

    # OSS public endpoint must not be internal
    public_ep = settings.effective_public_endpoint
    if "-internal.aliyuncs.com" in public_ep:
        issues.append(
            f"OSS_PUBLIC_ENDPOINT 使用了内网地址 ({public_ep})，"
            "桌面端无法访问。请改为公网 endpoint。"
        )

    return issues

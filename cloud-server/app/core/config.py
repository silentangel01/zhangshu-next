"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

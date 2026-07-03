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

    # Aliyun Monitor (RAM read-only sub-account)
    aliyun_monitor_access_key_id: str = ""
    aliyun_monitor_access_key_secret: str = ""
    swas_instance_id: str = ""
    swas_region_id: str = "cn-hangzhou"

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
    rate_limit_email_check_per_5m: int = 20
    rate_limit_email_code_send_per_5m: int = 5
    rate_limit_email_code_verify_per_5m: int = 10
    default_storage_quota_bytes: int = 1_073_741_824  # 1 GB
    default_backup_count_quota: int = 100

    # Auth email verification
    email_delivery_mode: str = "log"  # "smtp", "log", or "disabled"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    auth_email_code_secret: str = ""
    auth_email_code_length: int = 6
    auth_email_code_ttl_seconds: int = 600
    auth_email_code_resend_cooldown_seconds: int = 60
    auth_email_code_max_attempts: int = 5

    # Phone/SMS verification
    phone_auth_enabled: bool = False
    sms_delivery_mode: str = "log"  # "aliyun", "log", or "disabled"
    aliyun_sms_access_key_id: str = ""
    aliyun_sms_access_key_secret: str = ""
    aliyun_sms_sign_name: str = ""
    aliyun_sms_template_code: str = ""
    aliyun_sms_region_id: str = "cn-hangzhou"
    aliyun_sms_endpoint: str = "https://dysmsapi.aliyuncs.com/"
    auth_phone_code_secret: str = ""
    auth_phone_code_length: int = 6
    auth_phone_code_ttl_seconds: int = 600
    auth_phone_code_resend_cooldown_seconds: int = 60
    auth_phone_code_max_attempts: int = 5

    # OAuth login (WeChat / QQ)
    oauth_public_base_url: str = ""
    oauth_session_ttl_seconds: int = 600
    wechat_oauth_enabled: bool = False
    wechat_oauth_app_id: str = ""
    wechat_oauth_app_secret: str = ""
    qq_oauth_enabled: bool = False
    qq_oauth_app_id: str = ""
    qq_oauth_app_secret: str = ""

    # Admin
    admin_emails: str = ""

    # Admin security (Phase 2 — production hardening)
    admin_allowed_origins: str = ""
    admin_allow_bearer_fallback: bool = True
    admin_require_origin_check: bool = True
    require_separate_monitor_credentials: bool = False

    # Admin auth (HttpOnly Cookie)
    admin_access_token_expire_minutes: int = 30
    admin_refresh_token_expire_hours: int = 8
    admin_cookie_name: str = "zs_admin_token"
    admin_refresh_cookie_name: str = "zs_admin_refresh"
    admin_cookie_secure: bool = True
    admin_cookie_samesite: str = "lax"
    admin_cookie_path: str = "/api/admin"
    rate_limit_admin_login_per_5m: int = 5

    # Feedback limits
    feedback_max_attachments: int = 5
    feedback_max_attachment_size_bytes: int = 52_428_800  # 50 MB
    feedback_max_total_size_bytes: int = 157_286_400  # 150 MB
    feedback_allowed_content_types: str = (
        "image/png,image/jpeg,image/webp,image/gif,"
        "video/mp4,video/webm,video/quicktime"
    )
    rate_limit_feedback_create_per_hour: int = 5
    rate_limit_feedback_upload_per_hour: int = 20
    feedback_attachment_url_expire_seconds: int = 1800

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_enabled: bool = False

    # Rate limit / cache / audit backends
    rate_limit_backend: str = "database"  # "database" or "redis"
    cache_backend: str = "memory"  # "memory" or "redis"
    audit_async_enabled: bool = False
    audit_queue_name: str = "zs:audit_events"
    audit_batch_size: int = 100
    audit_flush_interval_seconds: int = 2

    # Database connection pool
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout_seconds: int = 5
    database_pool_recycle_seconds: int = 1800
    database_connect_timeout_seconds: int = 5
    database_statement_timeout_ms: int = 5000

    # Admin search / metrics
    admin_search_min_keyword_length: int = 2
    admin_metrics_cache_ttl_seconds: int = 60
    admin_metrics_stale_ttl_seconds: int = 600

    # Sync
    sync_max_changes_per_request: int = 200
    sync_max_payload_bytes: int = 1_048_576  # 1 MB
    sync_snapshot_retention_per_entity: int = 10

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

    @property
    def admin_email_list(self) -> list[str]:
        """Whitelisted admin emails (comma-separated)."""
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def admin_allowed_origin_list(self) -> list[str]:
        """Allowed origins for admin CSRF / Origin checks."""
        return [
            o.strip()
            for o in self.admin_allowed_origins.split(",")
            if o.strip()
        ]

    @property
    def feedback_allowed_content_type_set(self) -> set[str]:
        """Allowed MIME types for feedback attachments."""
        return {
            ct.strip()
            for ct in self.feedback_allowed_content_types.split(",")
            if ct.strip()
        }


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

    # JWT secret must not be default and must be long enough
    if settings.jwt_secret_key == "change-me-in-production":
        issues.append(
            "JWT_SECRET_KEY 使用默认值，生产环境必须设置随机密钥 (≥32 字符)。"
        )
    elif len(settings.jwt_secret_key) < 32:
        issues.append(
            "JWT_SECRET_KEY 长度不足 32 字符，生产环境请使用更长的随机密钥。"
        )

    # Admin cookie must be Secure
    if not settings.admin_cookie_secure:
        issues.append(
            "ADMIN_COOKIE_SECURE 必须为 true，生产环境要求 HTTPS Only Cookie。"
        )

    # Force HTTPS
    if not settings.force_https:
        issues.append(
            "FORCE_HTTPS 必须为 true，生产环境要求强制 HTTPS。"
        )

    # Admin Bearer fallback must be disabled in production
    if settings.admin_allow_bearer_fallback:
        issues.append(
            "ADMIN_ALLOW_BEARER_FALLBACK 在生产环境必须为 false，"
            "只允许 HttpOnly Cookie 认证。"
        )

    # CORS must not be wildcard
    if "*" in settings.cors_origin_list:
        issues.append(
            "CORS_ORIGINS 不允许使用通配符 *，请指定具体域名。"
        )

    # CORS must not allow non-localhost HTTP origins
    for origin in settings.cors_origin_list:
        if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin:
            issues.append(
                f"CORS_ORIGINS 包含非 localhost 的 HTTP 来源 ({origin})，"
                "生产环境应仅允许 HTTPS。"
            )

    # Admin allowed origins must be configured
    if not settings.admin_allowed_origin_list:
        issues.append(
            "ADMIN_ALLOWED_ORIGINS 未配置，生产环境必须明确指定管理员端允许的来源。"
        )

    # OSS credentials
    if not settings.oss_access_key_id or not settings.oss_access_key_secret:
        issues.append(
            "OSS_ACCESS_KEY_ID 或 OSS_ACCESS_KEY_SECRET 为空，云备份功能将不可用。"
        )

    # OSS public endpoint must not be internal
    public_ep = settings.effective_public_endpoint
    if "-internal.aliyuncs.com" in public_ep:
        issues.append(
            f"OSS_PUBLIC_ENDPOINT 使用了内网地址 ({public_ep})，"
            "桌面端无法访问。请改为公网 endpoint。"
        )

    # Monitor credentials separation
    if settings.require_separate_monitor_credentials:
        if (
            not settings.aliyun_monitor_access_key_id
            or not settings.aliyun_monitor_access_key_secret
        ):
            issues.append(
                "ALIYUN_MONITOR_ACCESS_KEY 未配置，生产环境要求监控密钥与 OSS 密钥分离。"
            )
        elif (
            settings.aliyun_monitor_access_key_id == settings.oss_access_key_id
            and settings.oss_access_key_id
        ):
            issues.append(
                "监控密钥与 OSS 密钥相同，生产环境要求密钥分权。"
            )

    # Production must use PostgreSQL, not SQLite
    if settings.database_url.startswith("sqlite"):
        issues.append(
            "DATABASE_URL 使用 SQLite，生产环境必须使用 PostgreSQL。"
        )

    # Redis must be enabled in production
    if not settings.redis_enabled:
        issues.append(
            "REDIS_ENABLED 必须为 true，生产环境要求 Redis 可用。"
        )

    # Rate limit backend must be redis in production
    if settings.rate_limit_backend != "redis":
        issues.append(
            f"RATE_LIMIT_BACKEND 为 '{settings.rate_limit_backend}'，"
            "生产环境建议使用 'redis'。"
        )

    # Email verification must use real SMTP in production
    email_delivery_mode = settings.email_delivery_mode.lower().strip()
    if email_delivery_mode != "smtp":
        issues.append(
            "EMAIL_DELIVERY_MODE 生产环境必须为 smtp，不能使用 log 或 disabled。"
        )
    if email_delivery_mode == "smtp":
        if not settings.smtp_host or not settings.smtp_from:
            issues.append(
                "SMTP_HOST 和 SMTP_FROM 生产环境必须配置，"
                "否则无法发送登录/注册验证码。"
            )
    if settings.smtp_use_tls and settings.smtp_use_ssl:
        issues.append(
            "SMTP_USE_TLS 和 SMTP_USE_SSL 不能同时为 true。"
        )

    if settings.phone_auth_enabled:
        sms_delivery_mode = settings.sms_delivery_mode.lower().strip()
        if sms_delivery_mode != "aliyun":
            issues.append(
                "PHONE_AUTH_ENABLED=true 时，生产环境 SMS_DELIVERY_MODE 必须为 aliyun。"
            )
        if sms_delivery_mode == "aliyun":
            if (
                not settings.aliyun_sms_access_key_id
                or not settings.aliyun_sms_access_key_secret
                or not settings.aliyun_sms_sign_name
                or not settings.aliyun_sms_template_code
            ):
                issues.append(
                    "阿里云短信 AccessKey、签名和模板未完整配置，无法发送手机验证码。"
                )

    if settings.wechat_oauth_enabled or settings.qq_oauth_enabled:
        if not settings.oauth_public_base_url.startswith("https://"):
            issues.append(
                "启用微信/QQ 登录时，OAUTH_PUBLIC_BASE_URL 必须配置为公网 HTTPS 地址。"
            )
        if settings.wechat_oauth_enabled and (
            not settings.wechat_oauth_app_id or not settings.wechat_oauth_app_secret
        ):
            issues.append("微信登录已启用，但 WECHAT_OAUTH_APP_ID/SECRET 未完整配置。")
        if settings.qq_oauth_enabled and (
            not settings.qq_oauth_app_id or not settings.qq_oauth_app_secret
        ):
            issues.append("QQ 登录已启用，但 QQ_OAUTH_APP_ID/SECRET 未完整配置。")

    # Cache backend must be redis in production
    if settings.cache_backend != "redis":
        issues.append(
            f"CACHE_BACKEND 为 '{settings.cache_backend}'，"
            "生产环境建议使用 'redis'。"
        )

    # DB pool parameters must be positive
    if (
        settings.database_pool_size <= 0
        or settings.database_max_overflow <= 0
        or settings.database_pool_timeout_seconds <= 0
    ):
        issues.append(
            "DATABASE_POOL_SIZE / DATABASE_MAX_OVERFLOW / "
            "DATABASE_POOL_TIMEOUT_SECONDS 必须为正数。"
        )

    return issues

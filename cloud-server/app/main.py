"""Zhangshu Cloud API — FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.account import router as account_router
from app.api.admin_announcements import router as admin_announcements_router
from app.api.admin_auth import router as admin_auth_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.admin_feedback import router as admin_feedback_router
from app.api.admin_monitoring import router as admin_monitoring_router
from app.api.admin_users import router as admin_users_router
from app.api.announcements import router as announcements_router
from app.api.auth import router as auth_router
from app.api.backups import router as backups_router
from app.api.feedback import router as feedback_router
from app.api.projects import router as projects_router
from app.core.config import get_settings, validate_production_config
from app.core.logging import RequestIDMiddleware, configure_logging
from app.core.security import configure_bcrypt
from app.core.security_headers import SecurityHeadersMiddleware

settings = get_settings()

# Configure logging first — all subsequent log messages use the new format
configure_logging(settings)

logger = logging.getLogger(__name__)

# Configure bcrypt rounds from settings
configure_bcrypt(settings.bcrypt_rounds)

app = FastAPI(title="Zhangshu Cloud API", version="0.1.0")


# ---------------------------------------------------------------------------
# Middleware (order matters — outermost first)
# ---------------------------------------------------------------------------
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup_checks():
    # Log OSS configuration status (without secrets)
    has_key = bool(settings.oss_access_key_id)
    has_secret = bool(settings.oss_access_key_secret)
    key_preview = settings.oss_access_key_id[:6] + "..." if has_key else "(empty)"
    logger.info(
        "OSS config: key=%s, secret=%s, bucket=%s, endpoint=%s",
        key_preview,
        "set" if has_secret else "(empty)",
        settings.oss_bucket_name,
        settings.oss_endpoint,
    )
    if not has_key or not has_secret:
        logger.warning(
            "OSS credentials are missing. Cloud backup will not work. "
            "Set OSS_ACCESS_KEY_ID and OSS_ACCESS_KEY_SECRET in .env"
        )

    # Production configuration validation
    issues = validate_production_config(settings)
    if issues:
        if settings.environment == "production":
            for issue in issues:
                logger.error("Production config error: %s", issue)
            raise RuntimeError(
                f"Production configuration has {len(issues)} error(s). "
                "Refusing to start. Check logs for details."
            )
        else:
            for issue in issues:
                logger.warning("Config advisory: %s", issue)

    logger.info(
        "Cloud API starting — environment=%s, log_level=%s",
        settings.environment,
        settings.log_level,
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(backups_router)
app.include_router(account_router)
app.include_router(announcements_router)
app.include_router(feedback_router)
app.include_router(admin_announcements_router)
app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_feedback_router)
app.include_router(admin_monitoring_router)
app.include_router(admin_users_router)


# ---------------------------------------------------------------------------
# Health / readiness endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Lightweight liveness probe — no external dependencies."""
    return {"status": "ok"}


@app.get("/ready")
def readiness_check():
    """Readiness probe — verifies DB connectivity and config status."""
    from app.db.session import engine

    checks: dict[str, str] = {}

    # Database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # OSS configuration (presence only — no actual network call)
    has_key = bool(settings.oss_access_key_id)
    has_secret = bool(settings.oss_access_key_secret)
    if has_key and has_secret:
        checks["oss_config"] = "ok"
    else:
        checks["oss_config"] = "not_configured"

    # Alembic version (best-effort)
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory

        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        checks["alembic_head"] = head or "none"
    except Exception:
        checks["alembic_head"] = "unknown"

    all_ok = checks.get("database") == "ok"
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }

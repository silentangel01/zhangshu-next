"""Zhangshu Cloud API — FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.backups import router as backups_router
from app.api.projects import router as projects_router
from app.core.config import get_settings
from app.core.security import configure_bcrypt

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure bcrypt rounds from settings
configure_bcrypt(settings.bcrypt_rounds)

app = FastAPI(title="Zhangshu Cloud API", version="0.1.0")


@app.on_event("startup")
def _log_oss_config():
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(backups_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

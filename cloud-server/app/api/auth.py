"""Authentication API routes."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-process rate limiter: key -> list of timestamps
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 300  # 5 minutes
_RATE_LIMIT_MAX_ATTEMPTS = 10


def _check_rate_limit(key: str) -> None:
    now = time.time()
    timestamps = _rate_limit_store[key]
    # Remove old entries
    _rate_limit_store[key] = [
        t for t in timestamps if now - t < _RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[key]) >= _RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后再试。",
        )


def _record_attempt(key: str) -> None:
    _rate_limit_store[key].append(time.time())


def _rate_limit_key(request: Request, email: str = "") -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{email.lower().strip()}"


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    key = _rate_limit_key(request, body.email)
    _check_rate_limit(key)
    _record_attempt(key)

    service = AuthService(db)
    try:
        result = service.register(body.email, body.password, body.display_name)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    key = _rate_limit_key(request, body.email)
    _check_rate_limit(key)
    _record_attempt(key)

    service = AuthService(db)
    try:
        result = service.login(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    try:
        result = service.refresh(body.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
    }

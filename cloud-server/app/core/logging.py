"""Structured logging, request ID, and sensitive field redaction."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sensitive patterns to redact from log output
# ---------------------------------------------------------------------------
_SENSITIVE_QUERY_KEYS = frozenset({
    "token", "access_token", "refresh_token", "authorization",
    "signature", "x-amz-signature", "ossaccesskeyid", "expires",
})

_SENSITIVE_VALUE_RE = re.compile(
    r"(Bearer\s+\S+|"
    r"https?://[^\s]*Signature=[^\s]*|"
    r"https?://[^\s]*X-Amz-Signature=[^\s]*|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})",
    re.IGNORECASE,
)


def redact_sensitive(value: str) -> str:
    """Replace known sensitive patterns with [REDACTED]."""
    return _SENSITIVE_VALUE_RE.sub("[REDACTED]", value)


def safe_log_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *extra* with sensitive values redacted."""
    safe: dict[str, Any] = {}
    for key, val in extra.items():
        if key.lower() in _SENSITIVE_QUERY_KEYS:
            safe[key] = "[REDACTED]"
        elif isinstance(val, str):
            safe[key] = redact_sensitive(val)
        else:
            safe[key] = val
    return safe


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra fields attached to the record
        for attr in ("request_id", "method", "path", "status_code",
                      "duration_ms", "client_ip", "event", "user_id",
                      "project_id", "backup_id", "result", "reason_code"):
            val = getattr(record, attr, None)
            if val is not None:
                entry[attr] = val
        # Include audit-prefixed extra fields
        for key, val in record.__dict__.items():
            if key.startswith("audit_"):
                entry[key] = val
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class _PlainFormatter(logging.Formatter):
    """Human-readable format for development."""

    FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"

    def __init__(self) -> None:
        super().__init__(self.FORMAT, datefmt="%H:%M:%S")


def configure_logging(settings: Any) -> None:
    """Configure root logging based on application settings.

    - Production: JSON structured logs
    - Development: human-readable plain logs
    """
    level = getattr(settings, "log_level", "INFO").upper()
    use_json = getattr(settings, "access_log_json", True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_PlainFormatter())
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Request ID + structured access log middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into every request and emit structured access log."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Accept an externally provided request ID or generate one
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Sanitize path: strip query string tokens
        path = request.url.path
        if request.url.query:
            safe_qs = "&".join(
                f"{k}=[REDACTED]" if k.lower() in _SENSITIVE_QUERY_KEYS else f"{k}={v}"
                for k, v in (
                    pair.split("=", 1) if "=" in pair else (pair, "")
                    for pair in request.url.query.split("&")
                )
            )
            path = f"{path}?{safe_qs}"

        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host

        access_logger = logging.getLogger("app.access")
        access_logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": redact_sensitive(path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response

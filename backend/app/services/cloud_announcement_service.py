"""Cloud announcement proxy service for the local backend sidecar."""

from __future__ import annotations

import logging

from app.infrastructure.cloud_api_client import (
    CloudApiError,
    CloudApiNotConfiguredError,
)
from app.services.cloud_auth_service import CloudAuthService

logger = logging.getLogger(__name__)


class CloudAnnouncementError(Exception):
    """Raised when the announcement proxy call fails."""


class CloudAnnouncementService:
    """Proxy service for fetching announcements from the cloud server.

    Silently returns an empty list when the cloud is not configured or
    unreachable — announcements must not interrupt local writing.
    """

    def __init__(self, auth_service: CloudAuthService):
        self._auth_service = auth_service

    def list_announcements(
        self,
        platform: str | None = None,
        app_version: str | None = None,
    ) -> dict:
        """Fetch active announcements from the cloud server.

        Returns ``{"items": [...], "total": N, "cloud_available": True}``
        on success, or ``{"items": [], "total": 0, "cloud_available": False}``
        when the cloud is not configured or unreachable.
        """
        try:
            result = self._auth_service.call_with_refresh(
                lambda c: c.list_announcements(
                    platform=platform, app_version=app_version
                )
            )
            return {**result, "cloud_available": True}
        except CloudApiNotConfiguredError:
            return {"items": [], "total": 0, "cloud_available": False}
        except CloudApiError as exc:
            logger.warning("Failed to fetch announcements: %s", exc)
            return {"items": [], "total": 0, "cloud_available": False}
        except Exception:
            # CloudAuthError (refresh failed) or other unexpected errors
            logger.warning("Unexpected error fetching announcements", exc_info=True)
            return {"items": [], "total": 0, "cloud_available": False}

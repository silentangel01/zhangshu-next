"""Cloud feedback proxy service for the local backend sidecar.

The sidecar receives the user's form data and files, validates them,
computes SHA256 checksums, coordinates the multi-step upload flow with
the cloud server, and uploads attachments to OSS via presigned URLs.

The desktop client never holds OSS AccessKey.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import UploadFile

from app.infrastructure.cloud_api_client import (
    CloudApiError,
    CloudApiNotConfiguredError,
)
from app.services.cloud_auth_service import CloudAuthService

logger = logging.getLogger(__name__)

# Allowed MIME types for feedback attachments
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm",
    "video/quicktime",
}

# Limits
MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_SIZE = 52_428_800  # 50 MB
MAX_TOTAL_SIZE = 157_286_400  # 150 MB


class CloudFeedbackError(Exception):
    """Raised when feedback submission fails."""


class CloudFeedbackService:
    """Proxy service for submitting feedback with optional attachments."""

    def __init__(self, auth_service: CloudAuthService):
        self._auth_service = auth_service

    async def submit_feedback(
        self,
        *,
        category: str,
        title: str,
        description: str,
        contact_email: str | None = None,
        include_diagnostics: bool = False,
        files: list[UploadFile] | None = None,
    ) -> dict[str, Any]:
        """Submit feedback to the cloud server.

        Flow:
        1. Validate files (count, size, type).
        2. Read file contents, compute SHA256.
        3. Call cloud-server ``POST /api/feedback`` to create ticket + get upload URLs.
        4. Upload each file to its presigned URL.
        5. Call cloud-server ``POST /api/feedback/{id}/complete`` to confirm.
        """

        # Validate and read files
        attachment_payloads: list[dict[str, Any]] = []
        file_contents: list[tuple[bytes, str, str]] = []  # (content, content_type, filename)

        if files:
            if len(files) > MAX_ATTACHMENTS:
                raise CloudFeedbackError(f"附件数量不能超过 {MAX_ATTACHMENTS} 个。")

            total_size = 0
            for f in files:
                if not f.filename or not f.content_type:
                    raise CloudFeedbackError("附件缺少文件名或类型。")
                if f.content_type not in ALLOWED_CONTENT_TYPES:
                    raise CloudFeedbackError(
                        f"不支持的附件类型: {f.content_type}。"
                        "仅支持图片和视频 (png, jpeg, webp, gif, mp4, webm, mov)。"
                    )

                content = await f.read()
                size = len(content)
                if size > MAX_ATTACHMENT_SIZE:
                    raise CloudFeedbackError(
                        f"附件 {f.filename} 超过大小限制 ({MAX_ATTACHMENT_SIZE // 1_048_576} MB)。"
                    )
                total_size += size
                if total_size > MAX_TOTAL_SIZE:
                    raise CloudFeedbackError(
                        f"附件总大小超过限制 ({MAX_TOTAL_SIZE // 1_048_576} MB)。"
                    )

                checksum = hashlib.sha256(content).hexdigest()
                attachment_payloads.append({
                    "filename": f.filename,
                    "content_type": f.content_type,
                    "size_bytes": size,
                    "checksum_sha256": checksum,
                })
                file_contents.append((content, f.content_type, f.filename))

        # Build cloud request payload
        payload: dict[str, Any] = {
            "category": category,
            "title": title,
            "description": description,
            "attachments": attachment_payloads,
        }
        if contact_email:
            payload["contact_email"] = contact_email
        if include_diagnostics:
            payload["client_diagnostics"] = self._build_diagnostics()

        # Step 1: Create feedback ticket on cloud server
        # Use call_with_refresh to transparently refresh token on 401
        try:
            create_response = self._auth_service.call_with_refresh(
                lambda c: c.create_feedback(payload)
            )
        except CloudApiNotConfiguredError as exc:
            raise CloudFeedbackError("章枢云服务暂未配置，无法提交反馈。") from exc
        except CloudApiError as exc:
            raise CloudFeedbackError(str(exc)) from exc
        except Exception as exc:
            # CloudAuthError (refresh failed) or other
            raise CloudFeedbackError(str(exc)) from exc

        feedback_id = create_response.get("id", "")
        upload_slots = create_response.get("upload_slots", [])

        # Rebuild client after potential token refresh so subsequent calls use new token
        client = self._auth_service.get_api_client()

        # Step 2: Upload each attachment to OSS via presigned URL
        uploaded = 0
        failed = 0
        upload_confirmations: list[dict[str, str]] = []

        for i, slot in enumerate(upload_slots):
            upload_url = slot.get("upload_url", "")
            upload_id = slot.get("upload_id", "")
            if i < len(file_contents):
                content, content_type, filename = file_contents[i]
                try:
                    client.upload_feedback_attachment(
                        upload_url, content, content_type
                    )
                    checksum = hashlib.sha256(content).hexdigest()
                    upload_confirmations.append({
                        "upload_id": upload_id,
                        "checksum_sha256": checksum,
                    })
                    uploaded += 1
                except CloudApiError as exc:
                    logger.warning("Failed to upload feedback attachment %s: %s", filename, exc)
                    failed += 1

        # Step 3: Complete the feedback
        try:
            complete_response = client.complete_feedback(
                feedback_id, upload_confirmations
            )
        except CloudApiError as exc:
            logger.warning("Failed to complete feedback: %s", exc)
            # Text feedback is still saved on the server even if complete fails
            complete_response = {}

        return {
            "id": feedback_id,
            "status": complete_response.get("status", create_response.get("status", "open")),
            "uploaded_attachments": uploaded,
            "failed_attachments": failed,
        }

    @staticmethod
    def _build_diagnostics() -> dict[str, Any]:
        """Build basic client diagnostics (no sensitive data)."""
        import sys
        return {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        }

    def list_ticket_replies(self, feedback_id: str) -> dict[str, Any]:
        """Fetch admin replies for a feedback ticket from the cloud server."""
        try:
            result = self._auth_service.call_with_refresh(
                lambda c: c.list_feedback_replies(feedback_id)
            )
        except CloudApiNotConfiguredError as exc:
            raise CloudFeedbackError("章枢云服务暂未配置，无法查看回复。") from exc
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code in (405, 404):
                raise CloudFeedbackError(
                    "当前云服务版本暂不支持查看回复，请稍后再试。"
                ) from exc
            raise CloudFeedbackError(str(exc)) from exc
        return {
            "items": result if isinstance(result, list) else [],
            "total": len(result) if isinstance(result, list) else 0,
        }

    def list_user_feedback(
        self, *, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """List the authenticated user's feedback from the cloud server."""
        try:
            result = self._auth_service.call_with_refresh(
                lambda c: c.list_user_feedback(limit=limit, offset=offset)
            )
        except CloudApiNotConfiguredError as exc:
            raise CloudFeedbackError("章枢云服务暂未配置，无法查看反馈历史。") from exc
        except Exception as exc:
            # Detect "endpoint not available" (405/404) from the cloud server
            status_code = getattr(exc, "status_code", None)
            if status_code in (405, 404):
                raise CloudFeedbackError(
                    "当前云服务版本暂不支持查看反馈历史，请稍后再试。"
                ) from exc
            raise CloudFeedbackError(str(exc)) from exc
        return result if isinstance(result, dict) else {"items": [], "total": 0}

"""Service layer for cloud profile operations (avatar, signature, password).

Orchestrates avatar upload: validates file, computes SHA-256, coordinates
with cloud API for presigned URL upload, and confirms completion.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import UploadFile

from app.services.cloud_auth_service import CloudAuthError, CloudAuthService

logger = logging.getLogger(__name__)

# Avatar constraints
AVATAR_ALLOWED_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
AVATAR_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


class CloudProfileError(Exception):
    """Raised when a profile operation fails."""


class CloudProfileService:
    """Orchestrates cloud profile operations via CloudAuthService."""

    def __init__(self, auth_service: CloudAuthService):
        self._auth = auth_service

    # ── Profile ────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        """Fetch the user's profile from the cloud server."""
        return self._auth.get_account_profile()

    def update_profile(
        self,
        display_name: str | None = None,
        signature: str | None = None,
    ) -> dict:
        """Update the user's display name and/or signature."""
        return self._auth.update_account_profile(
            display_name=display_name, signature=signature
        )

    # ── Avatar ─────────────────────────────────────────────────────

    async def upload_avatar(self, file: UploadFile) -> dict:
        """Upload a new avatar image.

        Validates MIME type and size, computes SHA-256, coordinates the
        three-step upload (init → OSS PUT → complete) with the cloud server.

        Returns the cloud server's avatar response on success.
        """
        # Validate content type
        content_type = file.content_type or ""
        if content_type not in AVATAR_ALLOWED_TYPES:
            raise CloudProfileError(
                f"不支持的图片格式：{content_type}。仅支持 PNG、JPEG、WebP。"
            )

        # Read file content and validate size
        content = await file.read()
        size_bytes = len(content)
        if size_bytes > AVATAR_MAX_SIZE_BYTES:
            raise CloudProfileError(
                f"图片过大 ({size_bytes / (1024 * 1024):.1f} MB)。最大允许 2 MB。"
            )
        if size_bytes == 0:
            raise CloudProfileError("图片文件为空。")

        # Compute SHA-256
        checksum_sha256 = hashlib.sha256(content).hexdigest()

        # Use original filename or fallback
        filename = file.filename or "avatar"

        # Step 1: Initialize upload on cloud server
        init_result = self._auth.init_avatar_upload(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        upload_id = init_result.get("upload_id", "")
        upload_url = init_result.get("upload_url", "")
        object_key = init_result.get("object_key", "")

        if not upload_url or not upload_id:
            raise CloudProfileError("云服务未返回上传地址。")

        # Step 2: Upload bytes to OSS via presigned URL
        self._auth.upload_avatar_to_oss(upload_url, content, content_type)

        # Step 3: Complete upload on cloud server
        result = self._auth.complete_avatar_upload(
            upload_id=upload_id,
            object_key=object_key,
            content_type=content_type,
            checksum_sha256=checksum_sha256,
        )

        return result

    def delete_avatar(self) -> dict | None:
        """Delete the user's avatar."""
        return self._auth.delete_avatar()

    # ── Password ───────────────────────────────────────────────────

    def change_password(self, old_password: str, new_password: str) -> dict:
        """Change the user's password on the cloud server.

        After success, clears local tokens (forces re-login).
        """
        result = self._auth.change_password(old_password, new_password)
        # Clear local tokens after successful password change
        self._auth.logout()
        return result

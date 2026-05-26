"""OSS storage infrastructure — presigned URL generation and object management.

Supports dual endpoint configuration:
- Public endpoint: for generating presigned URLs that clients can access.
- Internal endpoint: for server-side operations (head_object, delete_object).
"""

from __future__ import annotations

import logging
import re

import oss2

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OSSError(Exception):
    """Raised when OSS operations fail."""


class OSSStorage:
    def __init__(self):
        self._settings = get_settings()
        if not self._settings.oss_access_key_id or not self._settings.oss_access_key_secret:
            logger.error(
                "OSSStorage initialized without credentials. "
                "Check OSS_ACCESS_KEY_ID and OSS_ACCESS_KEY_SECRET in .env"
            )
        self._auth = oss2.Auth(
            self._settings.oss_access_key_id,
            self._settings.oss_access_key_secret,
        )

        # Public bucket — for presigned URLs given to clients
        public_ep = self._settings.effective_public_endpoint
        self._public_bucket = oss2.Bucket(
            self._auth,
            public_ep,
            self._settings.oss_bucket_name,
        )

        # Internal bucket — for server-side operations (head, delete)
        internal_ep = self._settings.effective_internal_endpoint
        if internal_ep != public_ep:
            self._internal_bucket = oss2.Bucket(
                self._auth,
                internal_ep,
                self._settings.oss_bucket_name,
            )
        else:
            self._internal_bucket = self._public_bucket

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.oss_access_key_id
            and self._settings.oss_access_key_secret
            and self._settings.oss_bucket_name
        )

    def build_object_key(
        self,
        user_id: str,
        project_id: str,
        backup_id: str,
        filename: str,
    ) -> str:
        safe = self._sanitize_filename(filename)
        return f"backups/{user_id}/{project_id}/{backup_id}/{safe}"

    def generate_put_url(
        self,
        object_key: str,
        expires_seconds: int | None = None,
        content_type: str = "application/zip",
    ) -> str:
        expire = expires_seconds or self._settings.oss_presigned_url_expire_seconds
        try:
            url = self._public_bucket.sign_url(
                "PUT",
                object_key,
                expire,
                headers={"Content-Type": content_type},
            )
            # Defensive check: presigned URL must NOT use internal endpoint
            if "-internal.aliyuncs.com" in url:
                logger.error(
                    "Presigned PUT URL uses internal endpoint. "
                    "Check OSS_PUBLIC_ENDPOINT configuration."
                )
                raise OSSError(
                    "云存储上传地址配置为内网地址，桌面端无法访问。"
                    "请联系管理员修正 OSS_PUBLIC_ENDPOINT。"
                )
            return url
        except OSSError:
            raise
        except Exception as exc:
            logger.error("Failed to generate PUT presigned URL: %s", exc)
            raise OSSError("生成上传链接失败。") from exc

    def generate_get_url(
        self,
        object_key: str,
        expires_seconds: int | None = None,
    ) -> str:
        expire = expires_seconds or self._settings.oss_presigned_url_expire_seconds
        try:
            url = self._public_bucket.sign_url("GET", object_key, expire)
            # Defensive check
            if "-internal.aliyuncs.com" in url:
                logger.error(
                    "Presigned GET URL uses internal endpoint. "
                    "Check OSS_PUBLIC_ENDPOINT configuration."
                )
                raise OSSError(
                    "云存储下载地址配置为内网地址，桌面端无法访问。"
                    "请联系管理员修正 OSS_PUBLIC_ENDPOINT。"
                )
            return url
        except OSSError:
            raise
        except Exception as exc:
            logger.error("Failed to generate GET presigned URL: %s", exc)
            raise OSSError("生成下载链接失败。") from exc

    def head_object(self, object_key: str) -> dict:
        """Return metadata for an object. Uses internal bucket."""
        try:
            meta = self._internal_bucket.head_object(object_key)
            return {
                "size": meta.content_length,
                "content_type": meta.content_type,
            }
        except oss2.exceptions.NoSuchKey as exc:
            raise OSSError("OSS 对象不存在。") from exc
        except Exception as exc:
            logger.error("Failed to head OSS object: %s", exc)
            raise OSSError("检查 OSS 对象失败。") from exc

    def delete_object(self, object_key: str) -> None:
        """Delete an object. Uses internal bucket."""
        try:
            self._internal_bucket.delete_object(object_key)
        except Exception as exc:
            logger.error("Failed to delete OSS object: %s", exc)
            raise OSSError("删除 OSS 对象失败。") from exc

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove path separators and limit length."""
        name = filename.replace("/", "_").replace("\\", "_")
        name = re.sub(r"[^\w.\-]", "_", name)
        if len(name) > 200:
            name = name[:200]
        return name or "backup.zip"

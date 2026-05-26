"""Tests for OSS dual endpoint configuration.

Verifies that:
- Presigned URLs use the public endpoint.
- Internal operations (head/delete) use the internal endpoint.
- Falls back correctly when endpoints are not configured.
- Presigned URLs never contain '-internal.aliyuncs.com'.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestOssEndpointConfig:
    """Test the OSSStorage dual endpoint behavior."""

    def _make_settings(
        self,
        endpoint="oss-cn-hangzhou.aliyuncs.com",
        public_endpoint="",
        internal_endpoint="",
    ):
        """Create a mock settings object."""
        settings = MagicMock()
        settings.oss_access_key_id = "test-key"
        settings.oss_access_key_secret = "test-secret"
        settings.oss_bucket_name = "test-bucket"
        settings.oss_endpoint = endpoint
        settings.oss_public_endpoint = public_endpoint
        settings.oss_internal_endpoint = internal_endpoint
        settings.oss_presigned_url_expire_seconds = 1800

        # effective_public_endpoint: public or fallback to oss_endpoint
        settings.effective_public_endpoint = (
            public_endpoint or endpoint
        )
        # effective_internal_endpoint: internal or fallback to public
        settings.effective_internal_endpoint = (
            internal_endpoint or settings.effective_public_endpoint
        )
        return settings

    @patch("app.infrastructure.oss_storage.oss2")
    @patch("app.infrastructure.oss_storage.get_settings")
    def test_public_endpoint_for_presigned_url(
        self, mock_get_settings, mock_oss2
    ):
        """Presigned URLs must use the public endpoint."""
        settings = self._make_settings(
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            public_endpoint="oss-cn-hangzhou.aliyuncs.com",
            internal_endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
        )
        mock_get_settings.return_value = settings

        # Mock bucket.sign_url to return a URL based on the endpoint
        mock_public_bucket = MagicMock()
        mock_public_bucket.sign_url.return_value = (
            "https://test-bucket.oss-cn-hangzhou.aliyuncs.com/key?sig=abc"
        )
        mock_internal_bucket = MagicMock()

        mock_oss2.Auth.return_value = MagicMock()
        mock_oss2.Bucket.side_effect = [mock_public_bucket, mock_internal_bucket]

        from app.infrastructure.oss_storage import OSSStorage

        storage = OSSStorage()
        url = storage.generate_put_url("backups/test/key.zip")

        assert "-internal.aliyuncs.com" not in url
        mock_public_bucket.sign_url.assert_called_once()

    @patch("app.infrastructure.oss_storage.oss2")
    @patch("app.infrastructure.oss_storage.get_settings")
    def test_internal_endpoint_for_head_delete(
        self, mock_get_settings, mock_oss2
    ):
        """head_object and delete_object use the internal bucket."""
        settings = self._make_settings(
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            public_endpoint="oss-cn-hangzhou.aliyuncs.com",
            internal_endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
        )
        mock_get_settings.return_value = settings

        mock_public_bucket = MagicMock()
        mock_internal_bucket = MagicMock()
        mock_meta = MagicMock()
        mock_meta.content_length = 1024
        mock_meta.content_type = "application/zip"
        mock_internal_bucket.head_object.return_value = mock_meta

        mock_oss2.Auth.return_value = MagicMock()
        mock_oss2.Bucket.side_effect = [mock_public_bucket, mock_internal_bucket]
        mock_oss2.exceptions = MagicMock()
        mock_oss2.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})

        from app.infrastructure.oss_storage import OSSStorage

        storage = OSSStorage()
        result = storage.head_object("backups/test/key.zip")

        mock_internal_bucket.head_object.assert_called_once_with(
            "backups/test/key.zip"
        )
        assert result["size"] == 1024

    @patch("app.infrastructure.oss_storage.oss2")
    @patch("app.infrastructure.oss_storage.get_settings")
    def test_fallback_when_no_public_endpoint(
        self, mock_get_settings, mock_oss2
    ):
        """When public_endpoint is empty, falls back to oss_endpoint."""
        settings = self._make_settings(
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            public_endpoint="",
            internal_endpoint="",
        )
        mock_get_settings.return_value = settings

        mock_bucket = MagicMock()
        mock_bucket.sign_url.return_value = (
            "https://test-bucket.oss-cn-hangzhou.aliyuncs.com/key?sig=abc"
        )

        mock_oss2.Auth.return_value = MagicMock()
        # Same endpoint → only one Bucket created (internal = public)
        mock_oss2.Bucket.return_value = mock_bucket

        from app.infrastructure.oss_storage import OSSStorage

        storage = OSSStorage()
        url = storage.generate_put_url("backups/test/key.zip")

        assert "-internal.aliyuncs.com" not in url

    @patch("app.infrastructure.oss_storage.oss2")
    @patch("app.infrastructure.oss_storage.get_settings")
    def test_presigned_url_internal_raises_error(
        self, mock_get_settings, mock_oss2
    ):
        """If presigned URL accidentally uses internal endpoint, raise error."""
        settings = self._make_settings(
            endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
            public_endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
        )
        mock_get_settings.return_value = settings

        mock_bucket = MagicMock()
        mock_bucket.sign_url.return_value = (
            "https://test-bucket.oss-cn-hangzhou-internal.aliyuncs.com/key?sig=abc"
        )

        mock_oss2.Auth.return_value = MagicMock()
        mock_oss2.Bucket.return_value = mock_bucket

        from app.infrastructure.oss_storage import OSSStorage, OSSError

        storage = OSSStorage()
        with pytest.raises(OSSError, match="内网地址"):
            storage.generate_put_url("backups/test/key.zip")


class TestSettingsEffectiveEndpoints:
    """Test the Settings.effective_*_endpoint properties."""

    def test_effective_public_falls_back(self):
        os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
        os.environ["OSS_PUBLIC_ENDPOINT"] = ""
        # Need to re-import to get fresh Settings
        from app.core.config import Settings

        s = Settings()
        assert s.effective_public_endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_effective_public_uses_explicit(self):
        os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
        os.environ["OSS_PUBLIC_ENDPOINT"] = "oss-cn-beijing.aliyuncs.com"

        from app.core.config import Settings

        s = Settings()
        assert s.effective_public_endpoint == "oss-cn-beijing.aliyuncs.com"

        # Clean up
        os.environ.pop("OSS_PUBLIC_ENDPOINT", None)

    def test_effective_internal_falls_back_to_public(self):
        os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
        os.environ["OSS_INTERNAL_ENDPOINT"] = ""
        os.environ["OSS_PUBLIC_ENDPOINT"] = ""

        from app.core.config import Settings

        s = Settings()
        assert s.effective_internal_endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_effective_internal_uses_explicit(self):
        os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
        os.environ["OSS_INTERNAL_ENDPOINT"] = "oss-cn-hangzhou-internal.aliyuncs.com"

        from app.core.config import Settings

        s = Settings()
        assert s.effective_internal_endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"

        # Clean up
        os.environ.pop("OSS_INTERNAL_ENDPOINT", None)

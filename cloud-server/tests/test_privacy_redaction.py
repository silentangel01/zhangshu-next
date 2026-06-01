"""Tests for privacy redaction utilities and audit IP masking."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///./test_privacy.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-min-32-bytes"
os.environ["OSS_ACCESS_KEY_ID"] = "test-key-id"
os.environ["OSS_ACCESS_KEY_SECRET"] = "test-key-secret"
os.environ["OSS_BUCKET_NAME"] = "test-bucket"
os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"

from app.core.privacy import hash_ip, mask_email, mask_ip, safe_user_agent, sanitize_filename  # noqa: E402


class TestMaskEmail:
    def test_normal_email(self):
        assert mask_email("john@example.com") == "j***@example.com"

    def test_single_char_local(self):
        assert mask_email("a@example.com") == "***@example.com"

    def test_two_char_local(self):
        assert mask_email("ab@example.com") == "a***@example.com"

    def test_long_local(self):
        assert mask_email("verylongname@example.com") == "v***@example.com"

    def test_invalid_email(self):
        assert mask_email("not-an-email") == "not-an-email"

    def test_chinese_email(self):
        result = mask_email("张三@qq.com")
        assert result == "张***@qq.com"


class TestMaskIP:
    def test_ipv4(self):
        assert mask_ip("192.168.1.42") == "192.168.1.xxx"

    def test_ipv4_localhost(self):
        assert mask_ip("127.0.0.1") == "127.0.0.xxx"

    def test_ipv6(self):
        result = mask_ip("2001:db8::1")
        assert result == "2001:xxxx"

    def test_empty(self):
        assert mask_ip("") == "***"

    def test_invalid(self):
        assert mask_ip("not-an-ip") == "***"


class TestHashIP:
    def test_deterministic(self):
        h1 = hash_ip("192.168.1.42")
        h2 = hash_ip("192.168.1.42")
        assert h1 == h2

    def test_different_ips_differ(self):
        h1 = hash_ip("192.168.1.42")
        h2 = hash_ip("10.0.0.1")
        assert h1 != h2

    def test_length(self):
        h = hash_ip("192.168.1.42")
        assert len(h) == 16

    def test_empty(self):
        assert hash_ip("") == ""

    def test_not_reversible(self):
        """Hash should not contain the original IP."""
        h = hash_ip("192.168.1.42")
        assert "192.168" not in h


class TestSafeUserAgent:
    def test_normal(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        assert safe_user_agent(ua) == ua

    def test_truncation(self):
        ua = "x" * 500
        result = safe_user_agent(ua, max_len=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_empty(self):
        assert safe_user_agent("") == ""


class TestSanitizeFilename:
    def test_normal(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_path_traversal(self):
        assert sanitize_filename("../../etc/passwd") == "passwd"

    def test_windows_path(self):
        assert sanitize_filename("C:\\Users\\test\\file.txt") == "file.txt"

    def test_null_byte(self):
        assert sanitize_filename("file\x00.txt") == "file.txt"

    def test_empty(self):
        assert sanitize_filename("") == ""


class TestAuditIPMasking:
    """Verify that audit_event stores masked IP, not raw IP."""

    def test_audit_stores_masked_ip(self):
        """The audit_event function should store masked IP in the DB."""
        from unittest.mock import MagicMock
        from app.core.audit import audit_event

        mock_db = MagicMock()
        # Simulate a successful db.add + commit
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        audit_event(
            "test_event",
            client_ip="192.168.1.42",
            user_id="user-123",
            db=mock_db,
        )

        # Verify db.add was called with a row that has masked IP
        assert mock_db.add.called
        row = mock_db.add.call_args[0][0]
        assert row.client_ip == "192.168.1.xxx"
        assert row.client_ip_masked == "192.168.1.xxx"
        assert row.client_ip_hash is not None
        assert "192.168" not in row.client_ip_hash

    def test_audit_blocks_forbidden_keys(self):
        """Forbidden extra keys should be silently dropped."""
        from unittest.mock import MagicMock
        from app.core.audit import audit_event

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        audit_event(
            "test_event",
            extra={"password_hash": "abc123", "target_user_id": "uid-1"},
            db=mock_db,
        )

        assert mock_db.add.called
        row = mock_db.add.call_args[0][0]
        # password_hash should be blocked
        if row.extra_json:
            assert "password" not in row.extra_json
            assert "target_user_id" in row.extra_json
        else:
            # Only target_user_id passed, password was blocked
            pass

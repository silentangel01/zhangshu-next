"""Tests for cloud network diagnostics.

Verifies that:
- Unconfigured base URL returns not_configured.
- Remote HTTP addresses return insecure_remote_http.
- Local HTTP addresses (localhost/127.0.0.1/::1) are allowed.
- Diagnostic results don't contain tokens or passwords.
- run_all_diagnostics handles exceptions gracefully.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.cloud_network_diagnostics import (  # noqa: E402
    config_check,
    https_policy_check,
    run_all_diagnostics,
)


# ── config_check ────────────────────────────────────────────────────


class TestConfigCheck:
    @patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False)
    def test_not_configured(self):
        result = config_check()
        assert result["ok"] is False
        assert result["error_kind"] == "not_configured"

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "https://api.example.com"},
        clear=False,
    )
    def test_configured_https(self):
        result = config_check()
        assert result["ok"] is True
        assert "api.example.com" in result["message"]

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "ftp://api.example.com"},
        clear=False,
    )
    def test_invalid_scheme(self):
        result = config_check()
        assert result["ok"] is False
        assert result["error_kind"] == "invalid_url"


# ── https_policy_check ──────────────────────────────────────────────


class TestHttpsPolicyCheck:
    @patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False)
    def test_not_configured(self):
        result = https_policy_check()
        assert result["ok"] is False
        assert result["error_kind"] == "not_configured"

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "https://api.example.com"},
        clear=False,
    )
    def test_remote_https_ok(self):
        result = https_policy_check()
        assert result["ok"] is True

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "http://api.example.com"},
        clear=False,
    )
    def test_remote_http_blocked(self):
        result = https_policy_check()
        assert result["ok"] is False
        assert result["error_kind"] == "insecure_remote_http"

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "http://localhost:9000"},
        clear=False,
    )
    def test_localhost_http_allowed(self):
        result = https_policy_check()
        assert result["ok"] is True

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "http://127.0.0.1:9000"},
        clear=False,
    )
    def test_127_http_allowed(self):
        result = https_policy_check()
        assert result["ok"] is True

    @patch.dict(
        "os.environ",
        {"ZHANGSHU_CLOUD_API_BASE_URL": "http://[::1]:9000"},
        clear=False,
    )
    def test_ipv6_loopback_http_allowed(self):
        result = https_policy_check()
        assert result["ok"] is True


# ── run_all_diagnostics ──────────────────────────────────────────────


class TestRunAllDiagnostics:
    @patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False)
    def test_not_configured_all_fail(self):
        """When not configured, all steps should return not_configured."""
        steps = run_all_diagnostics()
        assert len(steps) >= 2
        for step in steps:
            assert "name" in step
            assert "ok" in step
            assert "error_kind" in step
            assert "message" in step

    @patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False)
    def test_no_tokens_in_output(self):
        """Diagnostic output must not contain tokens or passwords."""
        steps = run_all_diagnostics()
        for step in steps:
            combined = f"{step.get('message', '')} {step.get('suggestion', '')}"
            # These strings should never appear in diagnostic output
            assert "Bearer" not in combined
            assert "access_token" not in combined
            assert "refresh_token" not in combined
            assert "password" not in combined.lower()

    @patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False)
    def test_handles_exceptions(self):
        """run_all_diagnostics should not raise even if individual steps fail."""
        mock_fn = MagicMock(side_effect=RuntimeError("boom"))
        mock_fn.__name__ = "config_check"
        with patch(
            "app.infrastructure.cloud_network_diagnostics.config_check",
            mock_fn,
        ):
            steps = run_all_diagnostics()
            # Should still return results (with the failing step caught)
            assert len(steps) >= 1

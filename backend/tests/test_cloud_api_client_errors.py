"""Tests for ``_parse_remote_error()`` in ``cloud_api_client``.

Covers structured detail, top-level fallbacks, ``None`` fields, non-string
fields, and non-JSON bodies.  Uses ``httpx.Response`` directly — no real
network calls.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.cloud_api_client import (  # noqa: E402
    _parse_remote_error,
    _safe_str,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_response(status_code: int, body: bytes | str | None = None, *, json_body=None) -> httpx.Response:
    """Build a minimal ``httpx.Response`` for testing."""
    if json_body is not None:
        content = json.dumps(json_body).encode()
        headers = {"content-type": "application/json"}
    elif body is not None:
        content = body.encode() if isinstance(body, str) else body
        headers = {"content-type": "application/json"}
    else:
        content = b""
        headers = {}
    return httpx.Response(status_code=status_code, content=content, headers=headers)


# ── _safe_str ────────────────────────────────────────────────────────


class TestSafeStr:
    def test_normal_string(self):
        assert _safe_str("hello") == "hello"

    def test_none(self):
        assert _safe_str(None) == ""

    def test_empty_string(self):
        assert _safe_str("") == ""

    def test_whitespace_only(self):
        assert _safe_str("   ") == ""

    def test_dict(self):
        assert _safe_str({"key": "value"}) == ""

    def test_list(self):
        assert _safe_str(["a", "b"]) == ""

    def test_int(self):
        assert _safe_str(42) == ""


# ── _parse_remote_error ─────────────────────────────────────────────


class TestParseRemoteError:
    """Tests for structured error body parsing."""

    def test_structured_detail(self):
        """``detail.message`` is used when it's a valid string."""
        resp = _make_response(400, json_body={
            "detail": {
                "message": "邮箱已被注册",
                "error_kind": "http_status_error",
                "suggestion": "请登录",
            }
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "邮箱已被注册"
        assert kind == "http_status_error"
        assert suggestion == "请登录"

    def test_top_level_message(self):
        """Falls back to top-level ``message`` when detail is absent."""
        resp = _make_response(500, json_body={"message": "远端错误"})
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "远端错误"
        assert kind == ""
        assert suggestion == ""

    def test_top_level_error(self):
        """Falls back to top-level ``error`` when message is also absent."""
        resp = _make_response(401, json_body={"error": "未经授权"})
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "未经授权"

    def test_none_fields_fallback(self):
        """``None`` fields do NOT become ``"None"`` strings."""
        resp = _make_response(400, json_body={
            "detail": {"message": None, "suggestion": None}
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (400)"
        assert suggestion == ""
        assert "None" not in msg

    def test_non_json_body(self):
        """Non-JSON body falls back to status-code message."""
        resp = _make_response(502, body="<html>Bad Gateway</html>")
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (502)"
        assert kind == "http_status_error"
        assert suggestion == ""

    def test_string_detail(self):
        """Plain string detail is used directly."""
        resp = _make_response(422, json_body={"detail": "请求参数无效"})
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "请求参数无效"

    def test_dict_as_message_field(self):
        """Dict value in ``detail.message`` does NOT leak repr."""
        resp = _make_response(400, json_body={
            "detail": {"message": {"nested": "object"}}
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (400)"
        assert "{" not in msg

    def test_list_as_message_field(self):
        """List value in ``detail.message`` does NOT leak repr."""
        resp = _make_response(400, json_body={
            "detail": {"message": ["error1", "error2"]}
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (400)"
        assert "[" not in msg

    def test_empty_string_detail_fallback(self):
        """Empty string detail falls through to top-level keys."""
        resp = _make_response(400, json_body={
            "detail": "",
            "message": "顶层消息",
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "顶层消息"

    def test_non_dict_payload(self):
        """JSON array body falls back to status-code message."""
        resp = _make_response(500, body='["error1", "error2"]')
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (500)"
        assert kind == "http_status_error"

    def test_empty_body(self):
        """Empty body falls back to status-code message."""
        resp = _make_response(500, body=b"")
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "云服务返回错误 (500)"

    def test_top_level_error_kind_fallback(self):
        """Top-level ``error_kind`` is used when detail doesn't provide one."""
        resp = _make_response(503, json_body={
            "message": "服务不可用",
            "error_kind": "service_unavailable",
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "服务不可用"
        assert kind == "service_unavailable"

    def test_detail_message_preferred_over_top_level(self):
        """``detail.message`` takes priority over top-level ``message``."""
        resp = _make_response(400, json_body={
            "detail": {"message": "详细错误"},
            "message": "泛化错误",
        })
        msg, kind, suggestion = _parse_remote_error(resp)
        assert msg == "详细错误"

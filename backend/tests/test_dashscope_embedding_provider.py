"""Tests for the DashScope embedding provider (mock httpx, no real network)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.infrastructure.dashscope_embedding_provider import (  # noqa: E402
    MAX_BATCH_SIZE,
    DashScopeApiKeyMissingError,
    DashScopeEmbeddingError,
    DashScopeEmbeddingProvider,
)


def _make_mock_response(status_code, json_data=None, raise_for_status=None):
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    if json_data is not None:
        response.json.return_value = json_data
    if raise_for_status:
        response.raise_for_status.side_effect = raise_for_status
    else:
        response.raise_for_status.return_value = None
    return response


def _make_provider(api_key="test-key", model="text-embedding-v4", dim=1024):
    return DashScopeEmbeddingProvider(api_key=api_key, model=model, vector_dim=dim)


class TestProperties:
    def test_model_name(self):
        provider = _make_provider(model="custom-model")
        assert provider.model_name == "custom-model"

    def test_vector_dim(self):
        provider = _make_provider(dim=512)
        assert provider.vector_dim == 512

    def test_empty_api_key_raises(self):
        with pytest.raises(DashScopeApiKeyMissingError):
            DashScopeEmbeddingProvider(api_key="")


class TestEncode:
    @patch("app.infrastructure.dashscope_embedding_provider.httpx.Client")
    def test_encode_returns_correct_dimension(self, mock_client_cls):
        provider = _make_provider(dim=4)
        mock_response = _make_mock_response(
            200,
            json_data={"data": [{"embedding": [0.1, 0.2, 0.3, 0.4], "index": 0}]},
        )
        provider._client = MagicMock()
        provider._client.post.return_value = mock_response

        result = provider.encode("hello world")
        assert len(result) == 4
        assert result == [0.1, 0.2, 0.3, 0.4]

    def test_encode_empty_text_returns_zero_vector(self):
        provider = _make_provider(dim=4)
        result = provider.encode("")
        assert result == [0.0, 0.0, 0.0, 0.0]

    def test_encode_whitespace_returns_zero_vector(self):
        provider = _make_provider(dim=4)
        result = provider.encode("   ")
        assert result == [0.0, 0.0, 0.0, 0.0]


class TestEncodeBatch:
    def test_empty_batch(self):
        provider = _make_provider(dim=4)
        result = provider.encode_batch([])
        assert result == []

    @patch("app.infrastructure.dashscope_embedding_provider.httpx.Client")
    def test_batch_splits_large_batches(self, mock_client_cls):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()

        # Mock responses for 2 batches (30 texts = 25 + 5)
        batch1_data = [
            {"embedding": [0.1, 0.2], "index": i} for i in range(MAX_BATCH_SIZE)
        ]
        batch2_data = [
            {"embedding": [0.3, 0.4], "index": i} for i in range(5)
        ]
        mock_resp1 = _make_mock_response(200, json_data={"data": batch1_data})
        mock_resp2 = _make_mock_response(200, json_data={"data": batch2_data})
        provider._client.post.side_effect = [mock_resp1, mock_resp2]

        texts = [f"text_{i}" for i in range(30)]
        result = provider.encode_batch(texts)
        assert len(result) == 30
        assert provider._client.post.call_count == 2

    @patch("app.infrastructure.dashscope_embedding_provider.httpx.Client")
    def test_preserves_order_via_index(self, mock_client_cls):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()

        # Return items in reverse order to test sorting
        data = [
            {"embedding": [0.3, 0.4], "index": 1},
            {"embedding": [0.1, 0.2], "index": 0},
        ]
        mock_resp = _make_mock_response(200, json_data={"data": data})
        provider._client.post.return_value = mock_resp

        result = provider.encode_batch(["a", "b"])
        assert result[0] == [0.1, 0.2]
        assert result[1] == [0.3, 0.4]


class TestErrorHandling:
    def test_timeout_raises_dashscope_error(self):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()
        provider._client.post.side_effect = httpx.TimeoutException("timeout")

        with pytest.raises(DashScopeEmbeddingError, match="超时"):
            provider.encode("test")

    def test_connect_error_raises(self):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()
        provider._client.post.side_effect = httpx.ConnectError("connect failed")

        with pytest.raises(DashScopeEmbeddingError, match="无法连接"):
            provider.encode("test")

    def test_http_401_raises_auth_error(self):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_resp
        )
        provider._client.post.return_value = mock_resp

        with pytest.raises(DashScopeEmbeddingError, match="认证失败"):
            provider.encode("test")

    def test_http_429_raises_rate_limit_error(self):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests", request=MagicMock(), response=mock_resp
        )
        provider._client.post.return_value = mock_resp

        with pytest.raises(DashScopeEmbeddingError, match="频繁"):
            provider.encode("test")

    def test_malformed_response_raises(self):
        provider = _make_provider(dim=2)
        provider._client = MagicMock()

        mock_resp = _make_mock_response(200, json_data={"unexpected": "format"})
        provider._client.post.return_value = mock_resp

        with pytest.raises(DashScopeEmbeddingError, match="格式异常"):
            provider.encode("test")

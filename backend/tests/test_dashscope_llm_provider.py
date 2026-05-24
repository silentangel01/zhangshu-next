"""Tests for DashScopeLLMProvider — mock HTTP, generate, summarize, errors."""

import json

import httpx
import pytest

from app.infrastructure.dashscope_llm_provider import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DashScopeLLMAuthError,
    DashScopeLLMError,
    DashScopeLLMProvider,
    MAX_CONTEXT_CHARS,
)


def _mock_response(
    status_code: int = 200,
    content: str = "这是测试回答。",
) -> httpx.Response:
    """Build a mock httpx.Response mimicking DashScope chat completion."""
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                },
            }
        ],
    }
    return httpx.Response(
        status_code=status_code,
        json=body,
        request=httpx.Request("POST", "https://test.example.com"),
    )


def _mock_error_response(status_code: int) -> httpx.Response:
    """Build a mock error response."""
    return httpx.Response(
        status_code=status_code,
        json={"error": {"message": "test error"}},
        request=httpx.Request("POST", "https://test.example.com"),
    )


class TestProperties:
    def test_model_name_default(self):
        provider = DashScopeLLMProvider(api_key="sk-test")
        assert provider.model_name == DEFAULT_LLM_MODEL

    def test_model_name_custom(self):
        provider = DashScopeLLMProvider(api_key="sk-test", model="qwen-max")
        assert provider.model_name == "qwen-max"

    def test_empty_api_key_raises(self):
        with pytest.raises(DashScopeLLMAuthError):
            DashScopeLLMProvider(api_key="")


class TestGenerate:
    def test_generate_returns_response(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            return _mock_response(content="魔法体系包括三种类型。")

        monkeypatch.setattr(provider._client, "post", mock_post)

        result = provider.generate("魔法体系有哪些？", "魔法分为元素、咒语、符文三类。")
        assert result == "魔法体系包括三种类型。"

    def test_generate_empty_context(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            return _mock_response(content="没有相关内容。")

        monkeypatch.setattr(provider._client, "post", mock_post)

        result = provider.generate("魔法体系？", "")
        assert result == "没有相关内容。"

    def test_generate_long_context_truncated(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        captured_body = {}

        def mock_post(url, **kwargs):
            captured_body.update(kwargs.get("json", {}))
            return _mock_response(content="回答")

        monkeypatch.setattr(provider._client, "post", mock_post)

        long_context = "A" * (MAX_CONTEXT_CHARS + 1000)
        provider.generate("问题", long_context)

        # Verify the context was truncated in the user message
        user_msg = captured_body["messages"][1]["content"]
        assert len(user_msg) < MAX_CONTEXT_CHARS + 500


class TestSummarize:
    def test_summarize_returns_response(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            return _mock_response(content="摘要内容：魔法体系概述。")

        monkeypatch.setattr(provider._client, "post", mock_post)

        result = provider.summarize(
            texts=["魔法体系包括元素魔法。", "咒语魔法需要吟唱。"],
            instruction="请总结魔法体系的特点。",
        )
        assert "摘要" in result

    def test_summarize_empty_list(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            return _mock_response(content="无内容可摘要。")

        monkeypatch.setattr(provider._client, "post", mock_post)

        result = provider.summarize(texts=[], instruction="总结")
        assert isinstance(result, str)


class TestErrorHandling:
    def test_timeout_raises_llm_error(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(provider._client, "post", mock_post)

        with pytest.raises(DashScopeLLMError, match="超时"):
            provider.generate("问题", "上下文")

    def test_connect_error_raises(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(provider._client, "post", mock_post)

        with pytest.raises(DashScopeLLMError, match="连接"):
            provider.generate("问题", "上下文")

    def test_http_401_raises_auth_error(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-bad-key")

        def mock_post(url, **kwargs):
            return _mock_error_response(401)

        # Need to raise HTTPStatusError for 4xx
        original_post = provider._client.post

        def mock_post_with_raise(url, **kwargs):
            resp = _mock_error_response(401)
            resp.raise_for_status = lambda: (_ for _ in ()).throw(
                httpx.HTTPStatusError(
                    "Unauthorized",
                    request=resp.request,
                    response=resp,
                )
            )
            return resp

        monkeypatch.setattr(provider._client, "post", mock_post_with_raise)

        with pytest.raises(DashScopeLLMAuthError):
            provider.generate("问题", "上下文")

    def test_http_429_raises_rate_limit_error(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post_with_raise(url, **kwargs):
            resp = _mock_error_response(429)
            resp.raise_for_status = lambda: (_ for _ in ()).throw(
                httpx.HTTPStatusError(
                    "Too Many Requests",
                    request=resp.request,
                    response=resp,
                )
            )
            return resp

        monkeypatch.setattr(provider._client, "post", mock_post_with_raise)

        with pytest.raises(DashScopeLLMError, match="频繁"):
            provider.generate("问题", "上下文")

    def test_malformed_response_raises(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")

        def mock_post(url, **kwargs):
            return httpx.Response(
                status_code=200,
                json={"unexpected": "format"},
                request=httpx.Request("POST", "https://test.example.com"),
            )

        monkeypatch.setattr(provider._client, "post", mock_post)

        with pytest.raises(DashScopeLLMError, match="格式"):
            provider.generate("问题", "上下文")


class TestRequestFormat:
    def test_correct_endpoint_called(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test")
        captured_url = []

        def mock_post(url, **kwargs):
            captured_url.append(url)
            return _mock_response()

        monkeypatch.setattr(provider._client, "post", mock_post)
        provider.generate("问题", "内容")

        assert len(captured_url) == 1
        assert "/chat/completions" in captured_url[0]

    def test_auth_header_sent(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-my-secret-key")
        captured_headers = []

        def mock_post(url, **kwargs):
            captured_headers.append(kwargs.get("headers", {}))
            return _mock_response()

        monkeypatch.setattr(provider._client, "post", mock_post)
        provider.generate("问题", "内容")

        assert "Bearer sk-my-secret-key" in captured_headers[0].get("Authorization", "")

    def test_model_in_request_body(self, monkeypatch):
        provider = DashScopeLLMProvider(api_key="sk-test", model="qwen-max")
        captured_body = {}

        def mock_post(url, **kwargs):
            captured_body.update(kwargs.get("json", {}))
            return _mock_response()

        monkeypatch.setattr(provider._client, "post", mock_post)
        provider.generate("问题", "内容")

        assert captured_body.get("model") == "qwen-max"

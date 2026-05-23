"""Tests for the LLM provider infrastructure."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.llm_provider import StubLLMProvider  # noqa: E402


@pytest.fixture
def provider():
    return StubLLMProvider()


# ---------- Properties ----------


class TestProperties:
    def test_model_name(self, provider):
        assert provider.model_name == "stub-v1"


# ---------- Generate ----------


class TestGenerate:
    def test_generate_with_context(self, provider):
        answer = provider.generate("什么是魔法体系？", "魔法体系包括元素魔法和咒语魔法。")
        assert "[AI 模型尚未接入]" in answer
        assert "魔法体系包括元素魔法" in answer
        assert "stub 模式" in answer

    def test_generate_empty_context(self, provider):
        answer = provider.generate("问题", "")
        assert "[AI 模型尚未接入]" in answer
        assert "未检索到" in answer

    def test_generate_long_context_truncated(self, provider):
        long_context = "这是一段很长的上下文内容。" * 100
        answer = provider.generate("问题", long_context)
        assert "..." in answer
        assert len(answer) < len(long_context)


# ---------- Summarize ----------


class TestSummarize:
    def test_summarize_with_texts(self, provider):
        texts = [
            "魔法体系是世界的核心力量来源。",
            "咒语魔法需要精确的发音和手势。",
        ]
        summary = provider.summarize(texts, "总结以下内容")
        assert "[AI 模型尚未接入]" in summary
        assert "2 段" in summary
        assert "魔法体系" in summary

    def test_summarize_empty_list(self, provider):
        summary = provider.summarize([], "总结")
        assert "[AI 模型尚未接入]" in summary
        assert "没有可用" in summary

    def test_summarize_with_topic_in_instruction(self, provider):
        texts = ["一些内容"]
        summary = provider.summarize(texts, "总结以下内容，聚焦主题：魔法")
        assert "1 段" in summary

"""LLM provider abstraction for knowledge base RAG and summarization."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers.

    An LLM provider generates text responses and summaries based on
    provided context and instructions.
    """

    def generate(self, prompt: str, context: str) -> str:
        """Generate a response based on a prompt and context.

        Args:
            prompt: The user's question or prompt.
            context: Retrieved context text to base the answer on.

        Returns:
            Generated response text.
        """
        ...

    def summarize(self, texts: list[str], instruction: str) -> str:
        """Generate a summary of multiple text segments.

        Args:
            texts: List of text segments to summarize.
            instruction: Summarization instruction or focus topic.

        Returns:
            Generated summary text.
        """
        ...

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        ...


class StubLLMProvider:
    """Stub LLM provider that returns template responses.

    Used for development and testing before connecting to a real LLM.
    Clearly marks all output as stub/placeholder.
    """

    MODEL_NAME = "stub-v1"

    def generate(self, prompt: str, context: str) -> str:
        """Generate a stub response showing retrieved context."""
        if not context.strip():
            return (
                "[AI 模型尚未接入]\n\n"
                "未检索到相关知识库内容。\n\n"
                "---\n"
                "提示：当前使用 stub 模式。接入真实 LLM 后，此处将基于知识库内容生成回答。"
            )

        # Show first 500 chars of context
        context_preview = context[:500]
        if len(context) > 500:
            context_preview += "..."

        return (
            "[AI 模型尚未接入] 以下是基于知识库检索到的相关内容：\n\n"
            f"{context_preview}\n\n"
            "---\n"
            "提示：当前使用 stub 模式。接入真实 LLM 后，此处将生成基于上下文的回答。"
        )

    def summarize(self, texts: list[str], instruction: str) -> str:
        """Generate a stub summary of provided texts."""
        if not texts:
            return (
                "[AI 模型尚未接入]\n\n"
                "没有可用的知识库内容进行摘要。\n\n"
                "---\n"
                "提示：当前使用 stub 模式。接入真实 LLM 后，此处将生成结构化摘要。"
            )

        # Show first 100 chars of each text
        previews = []
        for i, text in enumerate(texts, 1):
            preview = text[:100]
            if len(text) > 100:
                preview += "..."
            previews.append(f"[{i}] {preview}")

        content_preview = "\n".join(previews)

        return (
            f"[AI 模型尚未接入] 以下是对 {len(texts)} 段知识库内容的摘要草稿：\n\n"
            f"{content_preview}\n\n"
            "---\n"
            "提示：当前使用 stub 模式。接入真实 LLM 后，此处将生成结构化摘要。"
        )

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

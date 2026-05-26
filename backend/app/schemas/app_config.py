"""Pydantic schemas for app configuration API."""

from typing import Any

from pydantic import BaseModel


class AppConfigSetRequest(BaseModel):
    """Request body for setting config values."""

    dashscope_api_key: str | None = None
    llm_enabled: bool | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None


class AppConfigResponse(BaseModel):
    """Response for GET/PUT /api/app-config."""

    dashscope_api_key: dict[str, Any] | None = None
    llm_enabled: bool = False
    llm_model: str = ""
    llm_base_url: str = ""
    llm_provider: str = "dashscope"


class TestDashScopeRequest(BaseModel):
    """Request body for testing DashScope connectivity."""

    api_key: str | None = None


class TestDashScopeResponse(BaseModel):
    """Response from the test-connection endpoint."""

    success: bool
    model_name: str = ""
    vector_dim: int = 0
    error: str = ""


class TestLLMRequest(BaseModel):
    """Request body for testing LLM (chat) connectivity."""

    api_key: str | None = None
    model: str | None = None


class TestLLMResponse(BaseModel):
    """Response from the test-llm endpoint."""

    success: bool
    model_name: str = ""
    response_preview: str = ""
    error: str = ""

"""App configuration API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.app_config import (
    AppConfigResponse,
    AppConfigSetRequest,
    TestDashScopeRequest,
    TestDashScopeResponse,
    TestLLMRequest,
    TestLLMResponse,
)
from app.services.app_config_service import (
    KEY_DASHSCOPE_API_KEY,
    KEY_LLM_BASE_URL,
    KEY_LLM_ENABLED,
    KEY_LLM_MODEL,
    KEY_LLM_PROVIDER,
    AppConfigService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["app-config"])


def get_app_config_service(
    db: Session = Depends(get_db),
) -> AppConfigService:
    return AppConfigService(db)


@router.get("/api/app-config", response_model=AppConfigResponse)
def get_app_config(
    service: AppConfigService = Depends(get_app_config_service),
) -> AppConfigResponse:
    """Read all app config (sensitive values masked)."""
    all_config = service.get_all_masked()
    return AppConfigResponse(
        dashscope_api_key=all_config.get(KEY_DASHSCOPE_API_KEY),
        llm_enabled=service.get_value(KEY_LLM_ENABLED) == "true",
        llm_model=service.get_value(KEY_LLM_MODEL) or "",
        llm_base_url=service.get_value(KEY_LLM_BASE_URL) or "",
        llm_provider=service.get_value(KEY_LLM_PROVIDER) or "dashscope",
    )


@router.put("/api/app-config", response_model=AppConfigResponse)
def set_app_config(
    body: AppConfigSetRequest,
    service: AppConfigService = Depends(get_app_config_service),
) -> AppConfigResponse:
    """Set config values. Empty string deletes the stored key."""
    if body.dashscope_api_key is not None:
        key = body.dashscope_api_key.strip()
        if key:
            service.set_value(KEY_DASHSCOPE_API_KEY, key)
        else:
            service.delete_value(KEY_DASHSCOPE_API_KEY)

    if body.llm_enabled is not None:
        service.set_value(KEY_LLM_ENABLED, "true" if body.llm_enabled else "false")

    if body.llm_model is not None:
        model = body.llm_model.strip()
        if model:
            service.set_value(KEY_LLM_MODEL, model)
        else:
            service.delete_value(KEY_LLM_MODEL)

    if body.llm_base_url is not None:
        url = body.llm_base_url.strip()
        if url:
            service.set_value(KEY_LLM_BASE_URL, url)
        else:
            service.delete_value(KEY_LLM_BASE_URL)

    all_config = service.get_all_masked()
    return AppConfigResponse(
        dashscope_api_key=all_config.get(KEY_DASHSCOPE_API_KEY),
        llm_enabled=service.get_value(KEY_LLM_ENABLED) == "true",
        llm_model=service.get_value(KEY_LLM_MODEL) or "",
        llm_base_url=service.get_value(KEY_LLM_BASE_URL) or "",
        llm_provider=service.get_value(KEY_LLM_PROVIDER) or "dashscope",
    )


@router.post(
    "/api/app-config/test-dashscope",
    response_model=TestDashScopeResponse,
)
def test_dashscope_connection(
    body: TestDashScopeRequest,
    service: AppConfigService = Depends(get_app_config_service),
) -> TestDashScopeResponse:
    """Test DashScope connectivity by sending one embedding request."""
    api_key = body.api_key
    if api_key is None:
        api_key = service.get_decrypted(KEY_DASHSCOPE_API_KEY)

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="未提供 API Key，无法测试连接。",
        )

    api_key = api_key.strip()

    try:
        from app.infrastructure.dashscope_embedding_provider import (
            DashScopeApiKeyMissingError,
            DashScopeEmbeddingError,
            DashScopeEmbeddingProvider,
        )

        provider = DashScopeEmbeddingProvider(api_key=api_key)
        vector = provider.encode("连接测试")
        if not vector:
            return TestDashScopeResponse(
                success=False, error="返回向量为空。"
            )
        return TestDashScopeResponse(
            success=True,
            model_name=provider.model_name,
            vector_dim=len(vector),
        )
    except Exception as exc:
        # Catch DashScopeApiKeyMissingError, DashScopeEmbeddingError, etc.
        if type(exc).__name__ == "DashScopeApiKeyMissingError":
            return TestDashScopeResponse(success=False, error=str(exc))
        if type(exc).__name__ == "DashScopeEmbeddingError":
            return TestDashScopeResponse(success=False, error=str(exc))
        logger.warning("DashScope test error: %s", exc)
        return TestDashScopeResponse(
            success=False, error=f"测试失败：{type(exc).__name__}"
        )


@router.post(
    "/api/app-config/test-llm",
    response_model=TestLLMResponse,
)
def test_llm_connection(
    body: TestLLMRequest,
    service: AppConfigService = Depends(get_app_config_service),
) -> TestLLMResponse:
    """Test LLM connectivity by sending a minimal chat request."""
    api_key = body.api_key
    if api_key is None:
        api_key = service.get_decrypted(KEY_DASHSCOPE_API_KEY)

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="未提供 API Key，无法测试 AI 问答。",
        )

    model = body.model or service.get_value(KEY_LLM_MODEL) or ""
    base_url = service.get_value(KEY_LLM_BASE_URL) or ""

    try:
        from app.infrastructure.dashscope_llm_provider import (
            DashScopeLLMAuthError,
            DashScopeLLMError,
            DashScopeLLMProvider,
        )

        provider = DashScopeLLMProvider(
            api_key=api_key.strip(),
            model=model.strip() if model.strip() else None,
            base_url=base_url.strip() if base_url.strip() else None,
        )
        reply = provider.generate("你好", "")
        preview = reply[:50] if reply else ""
        return TestLLMResponse(
            success=True,
            model_name=provider.model_name,
            response_preview=preview,
        )
    except Exception as exc:
        # Catch DashScopeLLMAuthError, DashScopeLLMError, etc.
        if type(exc).__name__ == "DashScopeLLMAuthError":
            return TestLLMResponse(success=False, error=str(exc))
        if type(exc).__name__ == "DashScopeLLMError":
            return TestLLMResponse(success=False, error=str(exc))
        logger.warning("LLM test error: %s", exc)
        return TestLLMResponse(
            success=False, error=f"测试失败：{type(exc).__name__}"
        )

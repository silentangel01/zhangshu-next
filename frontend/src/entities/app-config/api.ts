import { apiRequest } from '@/shared/api/client'

import type {
  AppConfigResponse,
  AppConfigSetRequest,
  TestDashScopeRequest,
  TestDashScopeResponse,
  TestLLMRequest,
  TestLLMResponse,
} from './types'

export function getAppConfig(): Promise<AppConfigResponse> {
  return apiRequest<AppConfigResponse>('/api/app-config')
}

export function setAppConfig(payload: AppConfigSetRequest): Promise<AppConfigResponse> {
  return apiRequest<AppConfigResponse>('/api/app-config', {
    method: 'PUT',
    body: payload,
  })
}

export function testDashScopeConnection(
  payload: TestDashScopeRequest,
): Promise<TestDashScopeResponse> {
  return apiRequest<TestDashScopeResponse>('/api/app-config/test-dashscope', {
    method: 'POST',
    body: payload,
  })
}

export function testDashScopeLlmConnection(
  payload: TestLLMRequest,
): Promise<TestLLMResponse> {
  return apiRequest<TestLLMResponse>('/api/app-config/test-llm', {
    method: 'POST',
    body: payload,
  })
}

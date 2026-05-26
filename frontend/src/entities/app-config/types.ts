/** Masked representation of a sensitive config value. */
export interface AppConfigMaskedValue {
  has_value: boolean
  masked: string
  decrypt_error?: boolean
}

/** Response from GET/PUT /api/app-config. */
export interface AppConfigResponse {
  dashscope_api_key: AppConfigMaskedValue | null
  llm_enabled: boolean
  llm_model: string
  llm_base_url: string
  llm_provider: string
}

/** Request body for PUT /api/app-config. */
export interface AppConfigSetRequest {
  dashscope_api_key?: string | null
  llm_enabled?: boolean | null
  llm_model?: string | null
  llm_base_url?: string | null
}

/** Request body for POST /api/app-config/test-dashscope. */
export interface TestDashScopeRequest {
  api_key?: string | null
}

/** Response from POST /api/app-config/test-dashscope. */
export interface TestDashScopeResponse {
  success: boolean
  model_name: string
  vector_dim: number
  error: string
}

/** Request body for POST /api/app-config/test-llm. */
export interface TestLLMRequest {
  api_key?: string | null
  model?: string | null
}

/** Response from POST /api/app-config/test-llm. */
export interface TestLLMResponse {
  success: boolean
  model_name: string
  response_preview: string
  error: string
}

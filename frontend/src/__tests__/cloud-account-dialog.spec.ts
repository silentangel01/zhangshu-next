/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

// Mock the cloud API module
vi.mock('@/entities/cloud/api', () => ({
  getCloudAccountStatus: vi.fn(),
  cloudLogin: vi.fn(),
  cloudRegister: vi.fn(),
  cloudLogout: vi.fn(),
  getCloudNetworkSettings: vi.fn(),
  setCloudNetworkSettings: vi.fn(),
  runCloudNetworkDiagnostics: vi.fn(),
}))

// Mock ApiError
vi.mock('@/shared/api/client', () => {
  class MockApiError extends Error {
    status: number
    suggestion?: string
    errorKind?: string
    constructor(message: string, status: number, suggestion?: string, errorKind?: string) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.suggestion = suggestion
      this.errorKind = errorKind
    }
  }
  return {
    ApiError: MockApiError,
    apiRequest: vi.fn(),
    apiUpload: vi.fn(),
  }
})

import { ApiError } from '@/shared/api/client'
import {
  cloudLogin,
  getCloudAccountStatus,
  getCloudNetworkSettings,
  runCloudNetworkDiagnostics,
  setCloudNetworkSettings,
} from '@/entities/cloud/api'
import CloudAccountDialog from '@/features/cloud/CloudAccountDialog.vue'

const mockGetCloudAccountStatus = vi.mocked(getCloudAccountStatus)
const mockCloudLogin = vi.mocked(cloudLogin)
const mockGetCloudNetworkSettings = vi.mocked(getCloudNetworkSettings)
const mockRunCloudNetworkDiagnostics = vi.mocked(runCloudNetworkDiagnostics)
const mockSetCloudNetworkSettings = vi.mocked(setCloudNetworkSettings)

describe('CloudAccountDialog — diagnostic mode switch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetCloudAccountStatus.mockResolvedValue({
      logged_in: false,
      cloud_available: true,
      email: null,
      display_name: null,
    })
  })

  it('shows mode switch button after diagnostics and calls setCloudNetworkSettings', async () => {
    // Login fails with a network error → triggers diagnostic button
    mockCloudLogin.mockRejectedValue(
      new ApiError(
        '连接被重置',
        0,
        '可尝试系统代理或兼容模式。',
        'tls_reset_or_sni_filtered',
      ),
    )

    mockRunCloudNetworkDiagnostics.mockResolvedValue({
      ok: false,
      recommended_mode: 'system_proxy',
      summary: '可尝试系统代理或兼容模式。',
      steps: [
        {
          name: 'secure_https_check',
          ok: false,
          error_kind: 'tls_reset_or_sni_filtered',
          message: 'HTTPS 连接被重置',
          suggestion: '可尝试系统代理。',
          latency_ms: null,
        },
      ],
    })

    mockGetCloudNetworkSettings.mockResolvedValue({
      mode: 'auto',
      last_working_mode: null,
      base_url_configured: true,
    })

    mockSetCloudNetworkSettings.mockResolvedValue({
      mode: 'system_proxy',
      last_working_mode: null,
      base_url_configured: true,
    })

    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    // Fill in login form
    const emailInput = wrapper.find('input[type="email"]')
    const passwordInput = wrapper.find('input[type="password"]')
    await emailInput.setValue('test@example.com')
    await passwordInput.setValue('password123abc')

    // Submit login — expect failure
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // Diagnostic button should appear
    const diagButton = wrapper.find('.diagnose-button')
    expect(diagButton.exists()).toBe(true)

    // Run diagnostics
    await diagButton.trigger('click')
    await flushPromises()

    // Mode switch section should appear
    const modeSwitchSection = wrapper.find('.mode-switch')
    expect(modeSwitchSection.exists()).toBe(true)
    expect(wrapper.text()).toContain('建议切换为')

    const switchButton = wrapper.find('.switch-mode-button')
    expect(switchButton.exists()).toBe(true)
    expect(switchButton.text()).toContain('系统代理')

    // Click the mode switch button
    await switchButton.trigger('click')
    await flushPromises()

    // Verify setCloudNetworkSettings was called with recommended mode
    expect(mockSetCloudNetworkSettings).toHaveBeenCalledWith('system_proxy')

    // Verify success message
    expect(wrapper.text()).toContain('请重试登录或注册')
  })

  it('does not show mode switch when diagnostic reports ok', async () => {
    mockCloudLogin.mockRejectedValue(
      new ApiError('连接超时', 0, '请检查网络。', 'timeout'),
    )

    mockRunCloudNetworkDiagnostics.mockResolvedValue({
      ok: true,
      recommended_mode: 'auto',
      summary: '网络连接正常。',
      steps: [],
    })

    mockGetCloudNetworkSettings.mockResolvedValue({
      mode: 'auto',
      last_working_mode: null,
      base_url_configured: true,
    })

    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    // Trigger login failure
    const emailInput = wrapper.find('input[type="email"]')
    const passwordInput = wrapper.find('input[type="password"]')
    await emailInput.setValue('test@example.com')
    await passwordInput.setValue('password123abc')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    // Run diagnostics
    await wrapper.find('.diagnose-button').trigger('click')
    await flushPromises()

    // No mode switch section when diagnostic is ok
    expect(wrapper.find('.mode-switch').exists()).toBe(false)
  })

  it('does not show mode switch when recommended mode matches current', async () => {
    mockCloudLogin.mockRejectedValue(
      new ApiError('连接超时', 0, '请检查网络。', 'timeout'),
    )

    mockRunCloudNetworkDiagnostics.mockResolvedValue({
      ok: false,
      recommended_mode: 'auto',
      summary: '建议使用自动模式。',
      steps: [
        {
          name: 'check',
          ok: false,
          error_kind: 'timeout',
          message: '连接异常',
          suggestion: '使用自动模式。',
          latency_ms: null,
        },
      ],
    })

    // Current mode is already 'auto'
    mockGetCloudNetworkSettings.mockResolvedValue({
      mode: 'auto',
      last_working_mode: null,
      base_url_configured: true,
    })

    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    // Trigger login failure and run diagnostics
    const emailInput = wrapper.find('input[type="email"]')
    const passwordInput = wrapper.find('input[type="password"]')
    await emailInput.setValue('test@example.com')
    await passwordInput.setValue('password123abc')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    await wrapper.find('.diagnose-button').trigger('click')
    await flushPromises()

    // No mode switch when recommended matches current
    expect(wrapper.find('.mode-switch').exists()).toBe(false)
  })
})

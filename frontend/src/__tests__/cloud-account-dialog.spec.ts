/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

// Mock the cloud API module
vi.mock('@/entities/cloud/api', () => ({
  getCloudAccountStatus: vi.fn(),
  checkCloudEmail: vi.fn(),
  checkCloudPhone: vi.fn(),
  cloudLogin: vi.fn(),
  cloudLoginWithEmailCode: vi.fn(),
  cloudLoginWithPhoneCode: vi.fn(),
  cloudRegister: vi.fn(),
  cloudRegisterWithPhone: vi.fn(),
  cloudLogout: vi.fn(),
  startCloudOAuthLogin: vi.fn(),
  pollCloudOAuthLogin: vi.fn(),
  sendCloudEmailCode: vi.fn(),
  sendCloudPhoneCode: vi.fn(),
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
  checkCloudEmail,
  checkCloudPhone,
  cloudLogin,
  cloudLoginWithEmailCode,
  cloudLoginWithPhoneCode,
  cloudRegister,
  cloudRegisterWithPhone,
  getCloudAccountStatus,
  getCloudNetworkSettings,
  pollCloudOAuthLogin,
  runCloudNetworkDiagnostics,
  sendCloudEmailCode,
  sendCloudPhoneCode,
  setCloudNetworkSettings,
  startCloudOAuthLogin,
} from '@/entities/cloud/api'
import CloudAccountDialog from '@/features/cloud/CloudAccountDialog.vue'

const mockGetCloudAccountStatus = vi.mocked(getCloudAccountStatus)
const mockCheckCloudEmail = vi.mocked(checkCloudEmail)
const mockCheckCloudPhone = vi.mocked(checkCloudPhone)
const mockCloudLogin = vi.mocked(cloudLogin)
const mockCloudLoginWithEmailCode = vi.mocked(cloudLoginWithEmailCode)
const mockCloudLoginWithPhoneCode = vi.mocked(cloudLoginWithPhoneCode)
const mockCloudRegister = vi.mocked(cloudRegister)
const mockCloudRegisterWithPhone = vi.mocked(cloudRegisterWithPhone)
const mockStartCloudOAuthLogin = vi.mocked(startCloudOAuthLogin)
const mockPollCloudOAuthLogin = vi.mocked(pollCloudOAuthLogin)
const mockSendCloudEmailCode = vi.mocked(sendCloudEmailCode)
const mockSendCloudPhoneCode = vi.mocked(sendCloudPhoneCode)
const mockGetCloudNetworkSettings = vi.mocked(getCloudNetworkSettings)
const mockRunCloudNetworkDiagnostics = vi.mocked(runCloudNetworkDiagnostics)
const mockSetCloudNetworkSettings = vi.mocked(setCloudNetworkSettings)

describe('CloudAccountDialog — diagnostic mode switch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'open').mockImplementation(() => null)
    mockGetCloudAccountStatus.mockResolvedValue({
      logged_in: false,
      cloud_available: true,
      email: null,
      display_name: null,
    })
    mockCheckCloudEmail.mockResolvedValue({
      email: 'test@example.com',
      available: true,
    })
    mockCheckCloudPhone.mockResolvedValue({
      phone_number: '+8613800138000',
      available: true,
    })
    mockSendCloudEmailCode.mockResolvedValue({
      ok: true,
      expires_in_seconds: 600,
      cooldown_seconds: 60,
    })
    mockSendCloudPhoneCode.mockResolvedValue({
      ok: true,
      expires_in_seconds: 600,
      cooldown_seconds: 60,
    })
    mockCloudLoginWithEmailCode.mockResolvedValue({
      logged_in: true,
      cloud_available: true,
      email: 'test@example.com',
      display_name: 'test@example.com',
    })
    mockCloudLoginWithPhoneCode.mockResolvedValue({
      logged_in: true,
      cloud_available: true,
      email: null,
      phone_number: '+8613800138000',
      display_name: '138****8000',
    })
    mockCloudRegister.mockResolvedValue({
      logged_in: true,
      cloud_available: true,
      email: 'test@example.com',
      display_name: 'test@example.com',
    })
    mockCloudRegisterWithPhone.mockResolvedValue({
      logged_in: true,
      cloud_available: true,
      email: null,
      phone_number: '+8613800138000',
      display_name: '138****8000',
    })
    mockStartCloudOAuthLogin.mockResolvedValue({
      provider: 'wechat',
      authorization_url: 'https://open.weixin.qq.com/connect/qrconnect',
      session_id: 'session-1',
      poll_token: 'poll-1',
      expires_in_seconds: 600,
    })
    mockPollCloudOAuthLogin.mockResolvedValue({
      status: 'pending',
      provider: 'wechat',
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

  it('sends login email code and logs in with verification code', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    const emailInput = wrapper.find('input[type="email"]')
    await emailInput.setValue('test@example.com')

    await wrapper.find('.mode-link').trigger('click')
    await flushPromises()

    await wrapper.find('.code-button').trigger('click')
    await flushPromises()

    expect(mockSendCloudEmailCode).toHaveBeenCalledWith('test@example.com', 'login')

    const codeInput = wrapper.find('input[inputmode="numeric"]')
    await codeInput.setValue('123456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockCloudLoginWithEmailCode).toHaveBeenCalledWith('test@example.com', '123456')
  })

  it('sends login phone code and logs in with verification code', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.find('.mode-link').trigger('click')
    await flushPromises()

    await wrapper.findAll('.target-chip')[1]!.trigger('click')
    await flushPromises()

    const phoneInput = wrapper.find('input[inputmode="tel"]')
    await phoneInput.setValue('13800138000')

    await wrapper.find('.code-button').trigger('click')
    await flushPromises()

    expect(mockSendCloudPhoneCode).toHaveBeenCalledWith('13800138000', 'login')

    const codeInput = wrapper.find('input[inputmode="numeric"]')
    await codeInput.setValue('123456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockCloudLoginWithPhoneCode).toHaveBeenCalledWith('13800138000', '123456')
  })

  it('starts wechat oauth login and opens authorization url', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.find('.oauth-button.wechat').trigger('click')
    await flushPromises()

    expect(mockStartCloudOAuthLogin).toHaveBeenCalledWith('wechat')
    expect(window.open).toHaveBeenCalledWith(
      'https://open.weixin.qq.com/connect/qrconnect',
      '_blank',
      'noopener',
    )
    expect(mockPollCloudOAuthLogin).toHaveBeenCalledWith('session-1', 'poll-1')

    wrapper.unmount()
  })

  it('checks email before sending register code', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.findAll('.tab-button')[1]!.trigger('click')
    await flushPromises()

    const emailInput = wrapper.find('input[type="email"]')
    await emailInput.setValue('test@example.com')

    await wrapper.find('.code-button').trigger('click')
    await flushPromises()

    expect(mockCheckCloudEmail).toHaveBeenCalledWith('test@example.com')
    expect(mockSendCloudEmailCode).toHaveBeenCalledWith('test@example.com', 'register')
  })

  it('does not send register code when email is unavailable', async () => {
    mockCheckCloudEmail.mockResolvedValueOnce({
      email: 'taken@example.com',
      available: false,
    })

    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.findAll('.tab-button')[1]!.trigger('click')
    await flushPromises()

    const emailInput = wrapper.find('input[type="email"]')
    await emailInput.setValue('taken@example.com')

    await wrapper.find('.code-button').trigger('click')
    await flushPromises()

    expect(mockSendCloudEmailCode).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('该邮箱已注册')
  })

  it('registers with verification code', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.findAll('.tab-button')[1]!.trigger('click')
    await flushPromises()

    const emailInput = wrapper.find('input[type="email"]')
    await emailInput.setValue('test@example.com')
    const passwordInput = wrapper.find('input[type="password"]')
    await passwordInput.setValue('password123abc')
    const codeInput = wrapper.find('input[inputmode="numeric"]')
    await codeInput.setValue('123456')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockCloudRegister).toHaveBeenCalledWith(
      'test@example.com',
      'password123abc',
      '',
      '123456',
    )
  })

  it('registers with phone verification code', async () => {
    const wrapper = mount(CloudAccountDialog)
    await flushPromises()

    await wrapper.findAll('.tab-button')[1]!.trigger('click')
    await flushPromises()

    await wrapper.find('.mode-link').trigger('click')
    await flushPromises()

    const phoneInput = wrapper.find('input[inputmode="tel"]')
    await phoneInput.setValue('13800138000')

    await wrapper.find('.code-button').trigger('click')
    await flushPromises()

    expect(mockCheckCloudPhone).toHaveBeenCalledWith('13800138000')
    expect(mockSendCloudPhoneCode).toHaveBeenCalledWith('13800138000', 'register')

    const codeInput = wrapper.find('input[inputmode="numeric"]')
    await codeInput.setValue('123456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(mockCloudRegisterWithPhone).toHaveBeenCalledWith('13800138000', '123456', '')
  })
})

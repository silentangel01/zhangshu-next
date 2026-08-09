<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

import { ApiError } from '@/shared/api/client'
import {
  checkCloudEmail,
  checkCloudPhone,
  cloudLogin,
  cloudLoginWithEmailCode,
  cloudLoginWithPhoneCode,
  cloudLogout,
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
import type {
  CloudAccountStatus,
  CloudNetworkDiagnosticReport,
  CloudNetworkMode,
  CloudNetworkSettings,
  CloudOAuthProvider,
} from '@/entities/cloud/types'

const emit = defineEmits<{
  close: []
}>()

const isLoading = ref(true)
const isSubmitting = ref(false)
const isSendingLoginCode = ref(false)
const isSendingRegisterCode = ref(false)
const isStartingOAuth = ref(false)
const oauthPendingProvider = ref<CloudOAuthProvider | null>(null)
const activeTab = ref<'login' | 'register'>('login')
const loginMethod = ref<'password' | 'code'>('password')
const loginCodeTarget = ref<'email' | 'phone'>('email')
const registerMode = ref<'email' | 'phone'>('email')
const email = ref('')
const phoneNumber = ref('')
const password = ref('')
const displayName = ref('')
const loginVerificationCode = ref('')
const registerVerificationCode = ref('')
const errorMessage = ref('')
const errorSuggestion = ref('')
const successMessage = ref('')
const loginCodeCooldown = ref(0)
const registerCodeCooldown = ref(0)

const accountStatus = ref<CloudAccountStatus | null>(null)

const isLoggedIn = ref(false)
const cloudAvailable = ref(false)
const showDiagnosticButton = ref(false)
const diagnosticReport = ref<CloudNetworkDiagnosticReport | null>(null)
const isDiagnosing = ref(false)
const networkSettings = ref<CloudNetworkSettings | null>(null)
const isSwitchingMode = ref(false)

const MODE_LABELS: Record<CloudNetworkMode, string> = {
  auto: '自动',
  secure_direct: '安全直连',
  system_proxy: '系统代理',
  compat_no_sni: '兼容模式',
}

const OAUTH_LABELS: Record<CloudOAuthProvider, string> = {
  wechat: '微信',
  qq: 'QQ',
}

const LOGIN_AUTO_CLOSE_DELAY_MS = 1500

/** Error kinds that indicate network/TLS issues (not auth problems). */
const NETWORK_ERROR_KINDS = new Set([
  'tls_reset_or_sni_filtered',
  'tls_failed',
  'timeout',
  'tcp_unreachable',
  'dns_failed',
  'proxy_required_or_interfered',
  'cloud_unavailable',
])

let cooldownTimer: ReturnType<typeof setInterval> | null = null
let oauthPollTimer: ReturnType<typeof setInterval> | null = null
let autoCloseTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  try {
    const status = await getCloudAccountStatus()
    accountStatus.value = status
    isLoggedIn.value = status.logged_in
    cloudAvailable.value = status.cloud_available
  } catch {
    errorMessage.value = '无法读取云账户状态。'
  } finally {
    isLoading.value = false
  }
})

onUnmounted(() => {
  stopCooldownTimer()
  stopOAuthPolling()
  stopAutoCloseTimer()
})

function completeLogin(status: CloudAccountStatus, message: string) {
  accountStatus.value = status
  isLoggedIn.value = true
  cloudAvailable.value = status.cloud_available
  successMessage.value = message
  showDiagnosticButton.value = false
  scheduleAutoClose()
}

function scheduleAutoClose() {
  stopAutoCloseTimer()
  autoCloseTimer = setTimeout(() => {
    autoCloseTimer = null
    emit('close')
  }, LOGIN_AUTO_CLOSE_DELAY_MS)
}

function stopAutoCloseTimer() {
  if (!autoCloseTimer) return
  clearTimeout(autoCloseTimer)
  autoCloseTimer = null
}

async function handleLogin() {
  if (loginMethod.value === 'code') {
    await handleEmailCodeLogin()
    return
  }

  if (!email.value.trim() || !password.value) {
    errorMessage.value = '请输入邮箱和密码。'
    return
  }

  isSubmitting.value = true
  clearMessages()

  try {
    const status = await cloudLogin(email.value.trim(), password.value)
    completeLogin(status, '登录成功。')
    password.value = ''
  } catch (error) {
    handleError(error, '登录失败，请检查邮箱和密码。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleEmailCodeLogin() {
  const target = loginCodeTarget.value
  if (target === 'email' && (!email.value.trim() || !loginVerificationCode.value.trim())) {
    errorMessage.value = '请输入邮箱和验证码。'
    return
  }
  if (target === 'phone' && (!phoneNumber.value.trim() || !loginVerificationCode.value.trim())) {
    errorMessage.value = '请输入手机号和验证码。'
    return
  }

  isSubmitting.value = true
  clearMessages()

  try {
    const status =
      target === 'email'
        ? await cloudLoginWithEmailCode(email.value.trim(), loginVerificationCode.value.trim())
        : await cloudLoginWithPhoneCode(
            phoneNumber.value.trim(),
            loginVerificationCode.value.trim(),
          )
    completeLogin(status, '登录成功。')
    loginVerificationCode.value = ''
  } catch (error) {
    handleError(error, '验证码登录失败，请检查验证码。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleSendLoginCode() {
  if (loginCodeTarget.value === 'email' && !email.value.trim()) {
    errorMessage.value = '请输入邮箱。'
    return
  }
  if (loginCodeTarget.value === 'phone' && !phoneNumber.value.trim()) {
    errorMessage.value = '请输入手机号。'
    return
  }

  isSendingLoginCode.value = true
  clearMessages()

  try {
    const result =
      loginCodeTarget.value === 'email'
        ? await sendCloudEmailCode(email.value.trim(), 'login')
        : await sendCloudPhoneCode(phoneNumber.value.trim(), 'login')
    successMessage.value =
      loginCodeTarget.value === 'email'
        ? '如果邮箱已注册，验证码将发送到该邮箱。'
        : '如果手机号已注册，验证码将发送到该手机。'
    startCooldown('login', result.cooldown_seconds)
  } catch (error) {
    handleError(error, '验证码发送失败，请稍后重试。')
  } finally {
    isSendingLoginCode.value = false
  }
}

async function handleSendRegisterCode() {
  if (registerMode.value === 'email' && !email.value.trim()) {
    errorMessage.value = '请输入邮箱。'
    return
  }
  if (registerMode.value === 'phone' && !phoneNumber.value.trim()) {
    errorMessage.value = '请输入手机号。'
    return
  }

  isSendingRegisterCode.value = true
  clearMessages()

  try {
    const checked =
      registerMode.value === 'email'
        ? await checkCloudEmail(email.value.trim())
        : await checkCloudPhone(phoneNumber.value.trim())
    if (!checked.available) {
      errorMessage.value =
        registerMode.value === 'email'
          ? '该邮箱已注册，请直接登录。'
          : '该手机号已注册，请直接登录。'
      return
    }

    const result =
      registerMode.value === 'email'
        ? await sendCloudEmailCode(email.value.trim(), 'register')
        : await sendCloudPhoneCode(phoneNumber.value.trim(), 'register')
    successMessage.value =
      registerMode.value === 'email' ? '验证码已发送，请查看邮箱。' : '验证码已发送，请查看手机。'
    startCooldown('register', result.cooldown_seconds)
  } catch (error) {
    handleError(error, '验证码发送失败，请稍后重试。')
  } finally {
    isSendingRegisterCode.value = false
  }
}

async function handleRegister() {
  if (
    registerMode.value === 'email' &&
    (!email.value.trim() || !password.value || !registerVerificationCode.value.trim())
  ) {
    errorMessage.value = '请输入邮箱、密码和验证码。'
    return
  }
  if (
    registerMode.value === 'phone' &&
    (!phoneNumber.value.trim() || !registerVerificationCode.value.trim())
  ) {
    errorMessage.value = '请输入手机号和验证码。'
    return
  }

  isSubmitting.value = true
  clearMessages()

  try {
    const status =
      registerMode.value === 'email'
        ? await cloudRegister(
            email.value.trim(),
            password.value,
            displayName.value.trim(),
            registerVerificationCode.value.trim(),
          )
        : await cloudRegisterWithPhone(
            phoneNumber.value.trim(),
            registerVerificationCode.value.trim(),
            displayName.value.trim(),
          )
    completeLogin(status, '注册成功，已自动登录。')
    password.value = ''
    registerVerificationCode.value = ''
  } catch (error) {
    handleError(error, '注册失败，请稍后重试。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleLogout() {
  stopAutoCloseTimer()
  isSubmitting.value = true
  clearMessages()

  try {
    await cloudLogout()
    isLoggedIn.value = false
    accountStatus.value = null
    email.value = ''
    successMessage.value = '已退出登录。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '退出登录失败。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleOAuthLogin(provider: CloudOAuthProvider) {
  isStartingOAuth.value = true
  oauthPendingProvider.value = provider
  clearMessages()
  stopOAuthPolling()

  try {
    const result = await startCloudOAuthLogin(provider)
    window.open(result.authorization_url, '_blank', 'noopener')
    successMessage.value = `请在浏览器中完成${OAUTH_LABELS[provider]}授权。`
    startOAuthPolling(result.session_id, result.poll_token, provider)
  } catch (error) {
    oauthPendingProvider.value = null
    handleError(error, `${OAUTH_LABELS[provider]}登录暂不可用。`)
  } finally {
    isStartingOAuth.value = false
  }
}

function startOAuthPolling(sessionId: string, pollToken: string, provider: CloudOAuthProvider) {
  stopOAuthPolling()
  oauthPendingProvider.value = provider

  const poll = async () => {
    try {
      const result = await pollCloudOAuthLogin(sessionId, pollToken)
      if (result.status === 'pending') return
      stopOAuthPolling()

      if (result.status === 'failed') {
        errorMessage.value = result.error_message || `${OAUTH_LABELS[provider]}登录失败。`
        oauthPendingProvider.value = null
        return
      }

      const status: CloudAccountStatus = {
        logged_in: true,
        cloud_available: result.cloud_available ?? true,
        email: result.email ?? null,
        phone_number: result.phone_number ?? null,
        display_name: result.display_name || OAUTH_LABELS[provider],
      }
      completeLogin(status, `${OAUTH_LABELS[provider]}登录成功。`)
      oauthPendingProvider.value = null
    } catch (error) {
      stopOAuthPolling()
      oauthPendingProvider.value = null
      handleError(error, `${OAUTH_LABELS[provider]}登录状态确认失败。`)
    }
  }

  void poll()
  oauthPollTimer = setInterval(() => {
    void poll()
  }, 2000)
}

function stopOAuthPolling() {
  if (!oauthPollTimer) return
  clearInterval(oauthPollTimer)
  oauthPollTimer = null
}

function switchTab(tab: 'login' | 'register') {
  activeTab.value = tab
  password.value = ''
  loginVerificationCode.value = ''
  registerVerificationCode.value = ''
  clearMessages()
}

function switchLoginMethod(method: 'password' | 'code') {
  loginMethod.value = method
  password.value = ''
  loginVerificationCode.value = ''
  clearMessages()
}

function switchLoginCodeTarget(target: 'email' | 'phone') {
  loginCodeTarget.value = target
  loginVerificationCode.value = ''
  clearMessages()
}

function switchRegisterMode(mode: 'email' | 'phone') {
  registerMode.value = mode
  registerVerificationCode.value = ''
  password.value = ''
  clearMessages()
}

function clearMessages() {
  errorMessage.value = ''
  errorSuggestion.value = ''
  successMessage.value = ''
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.message) {
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function isNetworkError(error: unknown): boolean {
  if (error instanceof ApiError) {
    if (error.errorKind && NETWORK_ERROR_KINDS.has(error.errorKind)) {
      return true
    }
    // 5xx or 503 often indicate service/network issues
    if (error.status >= 500) {
      return true
    }
  }
  return false
}

function handleError(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    errorMessage.value = error.message || fallback
    if (error.suggestion) {
      errorSuggestion.value = error.suggestion
    }
    // Show diagnostic button for network errors, not auth errors
    showDiagnosticButton.value = isNetworkError(error)
  } else {
    errorMessage.value = getErrorMessage(error, fallback)
    showDiagnosticButton.value = false
  }
}

async function handleRunDiagnostics() {
  isDiagnosing.value = true
  diagnosticReport.value = null

  try {
    diagnosticReport.value = await runCloudNetworkDiagnostics()
    // Also fetch current settings to compare with recommended mode
    try {
      networkSettings.value = await getCloudNetworkSettings()
    } catch {
      // Settings fetch failure is non-critical
    }
  } catch {
    errorMessage.value = '诊断请求失败。'
  } finally {
    isDiagnosing.value = false
  }
}

async function handleSwitchMode(mode: CloudNetworkMode) {
  isSwitchingMode.value = true
  errorSuggestion.value = ''

  try {
    networkSettings.value = await setCloudNetworkSettings(mode)
    successMessage.value = `已切换为「${MODE_LABELS[mode]}」模式，请重试登录或注册。`
  } catch (error) {
    errorSuggestion.value = `切换连接模式失败：${getErrorMessage(error, '未知错误')}`
  } finally {
    isSwitchingMode.value = false
  }
}

/** Check if diagnostic recommends a mode different from current. */
function shouldShowModeSwitch(): boolean {
  if (!diagnosticReport.value || diagnosticReport.value.ok) return false
  if (!networkSettings.value) return false
  return diagnosticReport.value.recommended_mode !== networkSettings.value.mode
}

function startCooldown(kind: 'login' | 'register', seconds: number) {
  const value = Math.max(1, seconds)
  if (kind === 'login') {
    loginCodeCooldown.value = value
  } else {
    registerCodeCooldown.value = value
  }
  ensureCooldownTimer()
}

function ensureCooldownTimer() {
  if (cooldownTimer) return
  cooldownTimer = setInterval(() => {
    if (loginCodeCooldown.value > 0) {
      loginCodeCooldown.value -= 1
    }
    if (registerCodeCooldown.value > 0) {
      registerCodeCooldown.value -= 1
    }
    if (loginCodeCooldown.value <= 0 && registerCodeCooldown.value <= 0) {
      stopCooldownTimer()
    }
  }, 1000)
}

function stopCooldownTimer() {
  if (!cooldownTimer) return
  clearInterval(cooldownTimer)
  cooldownTimer = null
}
</script>

<template>
  <div class="zs-dialog" @click.self="emit('close')">
    <div class="zs-dialog-content cloud-account-dialog">
      <header class="dialog-header">
        <h2>章枢云账户</h2>
        <button class="close-button" type="button" @click="emit('close')">×</button>
      </header>

      <div class="dialog-body">
        <div v-if="isLoading" class="loading-state">正在加载…</div>

        <template v-else>
          <div v-if="!cloudAvailable" class="not-configured">
            <p class="info-text">
              云服务暂未配置。请联系管理员设置 <code>ZHANGSHU_CLOUD_API_BASE_URL</code>。
            </p>
          </div>

          <div v-else-if="isLoggedIn" class="logged-in-section">
            <div class="account-info">
              <p class="info-label">已登录</p>
              <p class="info-email">
                {{
                  accountStatus?.email ?? accountStatus?.phone_number ?? accountStatus?.display_name
                }}
              </p>
            </div>
            <button
              class="secondary-button"
              type="button"
              :disabled="isSubmitting"
              @click="handleLogout"
            >
              {{ isSubmitting ? '正在退出…' : '退出登录' }}
            </button>
          </div>

          <div v-else class="auth-section">
            <div class="tab-bar">
              <button
                :class="['tab-button', { active: activeTab === 'login' }]"
                type="button"
                @click="switchTab('login')"
              >
                登录
              </button>
              <button
                :class="['tab-button', { active: activeTab === 'register' }]"
                type="button"
                @click="switchTab('register')"
              >
                注册
              </button>
            </div>

            <form @submit.prevent="activeTab === 'login' ? handleLogin() : handleRegister()">
              <label
                v-if="
                  activeTab === 'register'
                    ? registerMode === 'email'
                    : loginMethod === 'password' || loginCodeTarget === 'email'
                "
              >
                <span>邮箱</span>
                <input v-model.trim="email" type="email" required placeholder="your@email.com" />
              </label>

              <label v-if="activeTab === 'register' && registerMode === 'phone'">
                <span>手机号</span>
                <input
                  v-model.trim="phoneNumber"
                  inputmode="tel"
                  required
                  placeholder="13800138000"
                />
              </label>

              <template v-if="activeTab === 'login' && loginMethod === 'password'">
                <label>
                  <span>密码</span>
                  <input v-model="password" type="password" required />
                </label>

                <button
                  class="primary-button"
                  type="submit"
                  :disabled="isSubmitting || !email.trim() || !password"
                >
                  {{ isSubmitting ? '正在登录…' : '登录' }}
                </button>

                <div class="mode-link-row">
                  <button class="mode-link" type="button" @click="switchLoginMethod('code')">
                    使用验证码登录
                  </button>
                </div>
              </template>

              <template v-else-if="activeTab === 'login'">
                <div class="code-target-row">
                  <button
                    :class="['target-chip', { active: loginCodeTarget === 'email' }]"
                    type="button"
                    @click="switchLoginCodeTarget('email')"
                  >
                    邮箱
                  </button>
                  <button
                    :class="['target-chip', { active: loginCodeTarget === 'phone' }]"
                    type="button"
                    @click="switchLoginCodeTarget('phone')"
                  >
                    手机号
                  </button>
                </div>

                <label v-if="loginCodeTarget === 'phone'">
                  <span>手机号</span>
                  <input
                    v-model.trim="phoneNumber"
                    inputmode="tel"
                    required
                    placeholder="13800138000"
                  />
                </label>

                <label>
                  <span>验证码</span>
                  <div class="code-row">
                    <input
                      v-model.trim="loginVerificationCode"
                      inputmode="numeric"
                      maxlength="10"
                      required
                    />
                    <button
                      class="secondary-button code-button"
                      type="button"
                      :disabled="
                        isSendingLoginCode ||
                        (loginCodeTarget === 'email' ? !email.trim() : !phoneNumber.trim()) ||
                        loginCodeCooldown > 0
                      "
                      @click="handleSendLoginCode"
                    >
                      {{
                        loginCodeCooldown > 0
                          ? `${loginCodeCooldown}s`
                          : isSendingLoginCode
                            ? '发送中…'
                            : '发送验证码'
                      }}
                    </button>
                  </div>
                </label>

                <button
                  class="primary-button"
                  type="submit"
                  :disabled="
                    isSubmitting ||
                    (loginCodeTarget === 'email' ? !email.trim() : !phoneNumber.trim()) ||
                    !loginVerificationCode.trim()
                  "
                >
                  {{ isSubmitting ? '正在登录…' : '登录' }}
                </button>

                <div class="mode-link-row">
                  <button class="mode-link" type="button" @click="switchLoginMethod('password')">
                    使用密码登录
                  </button>
                </div>
              </template>

              <template v-else>
                <div class="mode-link-row register-mode-row">
                  <button
                    v-if="registerMode === 'email'"
                    class="mode-link"
                    type="button"
                    @click="switchRegisterMode('phone')"
                  >
                    使用手机号注册
                  </button>
                  <button
                    v-else
                    class="mode-link"
                    type="button"
                    @click="switchRegisterMode('email')"
                  >
                    使用邮箱注册
                  </button>
                </div>

                <label>
                  <span>显示名称</span>
                  <input v-model.trim="displayName" type="text" placeholder="可选" />
                </label>

                <label v-if="registerMode === 'email'">
                  <span>密码</span>
                  <input v-model="password" type="password" required />
                  <span class="field-hint">至少 10 个字符，建议包含字母和数字</span>
                </label>

                <label>
                  <span>验证码</span>
                  <div class="code-row">
                    <input
                      v-model.trim="registerVerificationCode"
                      inputmode="numeric"
                      maxlength="10"
                      required
                    />
                    <button
                      class="secondary-button code-button"
                      type="button"
                      :disabled="
                        isSendingRegisterCode ||
                        (registerMode === 'email' ? !email.trim() : !phoneNumber.trim()) ||
                        registerCodeCooldown > 0
                      "
                      @click="handleSendRegisterCode"
                    >
                      {{
                        registerCodeCooldown > 0
                          ? `${registerCodeCooldown}s`
                          : isSendingRegisterCode
                            ? '发送中…'
                            : '发送验证码'
                      }}
                    </button>
                  </div>
                </label>

                <button
                  class="primary-button"
                  type="submit"
                  :disabled="
                    isSubmitting ||
                    (registerMode === 'email' ? !email.trim() : !phoneNumber.trim()) ||
                    (registerMode === 'email' && !password) ||
                    !registerVerificationCode.trim()
                  "
                >
                  {{ isSubmitting ? '正在注册…' : '注册' }}
                </button>
              </template>
            </form>

            <div class="oauth-login-section">
              <div class="oauth-divider"><span>第三方登录</span></div>
              <div class="oauth-buttons">
                <button
                  class="oauth-button wechat"
                  type="button"
                  :disabled="isStartingOAuth || oauthPendingProvider !== null"
                  @click="handleOAuthLogin('wechat')"
                >
                  {{ oauthPendingProvider === 'wechat' ? '等待授权…' : '微信登录' }}
                </button>
                <button
                  class="oauth-button qq"
                  type="button"
                  :disabled="isStartingOAuth || oauthPendingProvider !== null"
                  @click="handleOAuthLogin('qq')"
                >
                  {{ oauthPendingProvider === 'qq' ? '等待授权…' : 'QQ 登录' }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <p v-if="errorSuggestion" class="suggestion-text">{{ errorSuggestion }}</p>
        <p v-if="successMessage" class="success-text">{{ successMessage }}</p>

        <!-- Diagnostic button for non-auth failures -->
        <div v-if="showDiagnosticButton && !isLoggedIn" class="diagnostic-section">
          <button
            class="diagnose-button"
            type="button"
            :disabled="isDiagnosing"
            @click="handleRunDiagnostics"
          >
            {{ isDiagnosing ? '正在检测...' : '运行连接诊断' }}
          </button>

          <div v-if="diagnosticReport" class="diagnostic-result">
            <p :class="['diagnostic-summary', diagnosticReport.ok ? 'ok' : 'failed']">
              {{ diagnosticReport.summary }}
            </p>

            <!-- Mode switch button when recommended mode differs from current -->
            <div v-if="shouldShowModeSwitch()" class="mode-switch">
              <span class="switch-label">建议切换为：</span>
              <button
                class="switch-mode-button"
                type="button"
                :disabled="isSwitchingMode"
                @click="handleSwitchMode(diagnosticReport!.recommended_mode)"
              >
                {{
                  isSwitchingMode ? '正在切换...' : MODE_LABELS[diagnosticReport!.recommended_mode]
                }}
              </button>
            </div>

            <ul class="diagnostic-steps">
              <li v-for="step in diagnosticReport.steps.filter((s) => !s.ok)" :key="step.name">
                {{ step.message }}
                <span v-if="step.suggestion" class="step-suggestion">— {{ step.suggestion }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cloud-account-dialog {
  width: min(460px, calc(100vw - 32px));
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto 1fr;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  padding: var(--zs-space-4) var(--zs-space-5);
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.dialog-body {
  display: grid;
  gap: var(--zs-space-4);
  padding: var(--zs-space-4) var(--zs-space-5);
}

@media (max-width: 480px) {
  .dialog-header,
  .dialog-body {
    padding-left: var(--zs-space-4);
    padding-right: var(--zs-space-4);
  }
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.close-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--zs-radius-sm);
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 1.5rem;
  cursor: pointer;
}

.close-button:hover {
  background: var(--zs-color-surface-soft);
}

.loading-state {
  padding: var(--zs-space-6) 0;
  color: var(--zs-color-text-muted);
  text-align: center;
}

.not-configured {
  padding: var(--zs-space-4) 0;
}

.info-text {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.info-text code {
  padding: 2px 6px;
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface-soft);
  font-size: 0.85em;
}

.logged-in-section {
  display: grid;
  gap: var(--zs-space-4);
}

.account-info {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface-soft);
}

.info-label {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-email {
  margin: 0;
  color: var(--zs-color-text);
  font-weight: 800;
  font-size: 1.05rem;
}

.auth-section {
  display: grid;
  gap: var(--zs-space-5);
}

.tab-bar {
  display: flex;
  gap: var(--zs-space-2);
  padding: var(--zs-space-1);
  background: var(--zs-color-surface-soft);
  border-radius: var(--zs-radius-md);
}

.tab-button {
  flex: 1;
  min-height: 38px;
  border: none;
  border-radius: var(--zs-radius-sm);
  background: transparent;
  color: var(--zs-color-text-muted);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-button:hover:not(.active) {
  color: var(--zs-color-text);
  background: var(--zs-color-surface);
}

.tab-button.active {
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

form {
  display: grid;
  gap: var(--zs-space-4);
}

label {
  display: grid;
  gap: var(--zs-space-2);
  color: var(--zs-color-text-muted);
  font-weight: 800;
  font-size: 0.875rem;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 12px 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
  box-shadow: 0 0 0 3px rgba(var(--zs-color-primary-rgb, 59, 130, 246), 0.1);
}

.field-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 500;
}

.code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--zs-space-2);
  align-items: center;
}

.code-button {
  min-width: 112px;
  padding-inline: 12px;
  white-space: nowrap;
}

.code-target-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--zs-space-2);
  padding: var(--zs-space-1);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface-soft);
}

.target-chip {
  min-height: 34px;
  border-color: transparent;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  box-shadow: none;
}

.target-chip.active {
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  border-color: var(--zs-color-border-soft);
}

.target-chip:not(:disabled):hover {
  transform: none;
  background: var(--zs-color-surface);
}

.mode-link-row {
  display: flex;
  justify-content: flex-end;
  margin-top: calc(var(--zs-space-2) * -1);
}

.mode-link {
  min-height: 24px;
  border: none;
  padding: 0;
  background: transparent;
  color: var(--zs-color-primary);
  font-size: 0.82rem;
  font-weight: 700;
}

button {
  min-height: 42px;
  border-radius: var(--zs-radius-sm);
  border: 1px solid transparent;
  padding: 0 16px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

button:disabled {
  cursor: wait;
  opacity: 0.6;
}

button:not(:disabled):hover {
  transform: translateY(-1px);
}

.mode-link:not(:disabled):hover {
  transform: none;
  color: var(--zs-color-primary-hover, var(--zs-color-primary));
  text-decoration: underline;
}

.primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  box-shadow: 0 2px 4px rgba(var(--zs-color-primary-rgb, 59, 130, 246), 0.2);
}

.primary-button:not(:disabled):hover {
  box-shadow: 0 4px 8px rgba(var(--zs-color-primary-rgb, 59, 130, 246), 0.3);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.secondary-button:not(:disabled):hover {
  background: var(--zs-color-surface-soft);
}

.oauth-login-section {
  display: grid;
  gap: var(--zs-space-3);
}

.oauth-divider {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.oauth-divider::before,
.oauth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--zs-color-border-soft);
}

.oauth-buttons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--zs-space-2);
}

.oauth-button {
  min-height: 38px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border-color: var(--zs-color-border);
  font-size: 0.86rem;
}

.oauth-button.wechat:not(:disabled):hover {
  color: #14853d;
  border-color: #16a34a;
}

.oauth-button.qq:not(:disabled):hover {
  color: #0b68c8;
  border-color: #0ea5e9;
}

.error-text {
  margin: 0;
  padding: var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
  font-weight: 800;
  font-size: 0.875rem;
  line-height: 1.5;
}

.suggestion-text {
  margin: 0;
  padding: var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-warning-soft, #fffbeb);
  color: var(--zs-color-warning, #d97706);
  font-weight: 600;
  font-size: 0.85rem;
  line-height: 1.5;
}

.success-text {
  margin: 0;
  padding: var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success);
  font-weight: 800;
  font-size: 0.875rem;
  line-height: 1.5;
}

.diagnostic-section {
  display: grid;
  gap: var(--zs-space-3);
  padding: var(--zs-space-4);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface-soft);
}

.diagnose-button {
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.diagnose-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.diagnose-button:not(:disabled):hover {
  background: var(--zs-color-surface);
  border-color: var(--zs-color-primary);
  transform: translateY(-1px);
}

.diagnostic-result {
  display: grid;
  gap: var(--zs-space-3);
}

.diagnostic-summary {
  margin: 0;
  padding: var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  font-size: 0.875rem;
  line-height: 1.5;
  font-weight: 600;
}

.diagnostic-summary.ok {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #22c55e);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.diagnostic-summary.failed {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger, #ef4444);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.diagnostic-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-2);
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
}

.diagnostic-steps li {
  padding: var(--zs-space-2) var(--zs-space-3);
  background: var(--zs-color-surface);
  border-radius: var(--zs-radius-sm);
  line-height: 1.5;
}

.step-suggestion {
  display: block;
  margin-top: var(--zs-space-1);
  color: var(--zs-color-warning, #f59e0b);
  font-size: 0.8rem;
}

.mode-switch {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding: var(--zs-space-3);
  background: var(--zs-color-info-soft, #eff6ff);
  border-radius: var(--zs-radius-sm);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.switch-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  font-weight: 600;
}

.switch-mode-button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font: inherit;
  font-weight: 800;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.switch-mode-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.switch-mode-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(var(--zs-color-primary-rgb, 59, 130, 246), 0.3);
}
</style>

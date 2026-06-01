<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { ApiError } from '@/shared/api/client'
import {
  cloudLogin,
  cloudLogout,
  cloudRegister,
  getCloudAccountStatus,
  getCloudNetworkSettings,
  runCloudNetworkDiagnostics,
  setCloudNetworkSettings,
} from '@/entities/cloud/api'
import type {
  CloudAccountStatus,
  CloudNetworkDiagnosticReport,
  CloudNetworkMode,
  CloudNetworkSettings,
} from '@/entities/cloud/types'

const emit = defineEmits<{
  close: []
}>()

const isLoading = ref(true)
const isSubmitting = ref(false)
const activeTab = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const displayName = ref('')
const errorMessage = ref('')
const errorSuggestion = ref('')
const successMessage = ref('')

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

async function handleLogin() {
  if (!email.value.trim() || !password.value) {
    errorMessage.value = '请输入邮箱和密码。'
    return
  }

  isSubmitting.value = true
  clearMessages()

  try {
    const status = await cloudLogin(email.value.trim(), password.value)
    accountStatus.value = status
    isLoggedIn.value = true
    cloudAvailable.value = status.cloud_available
    successMessage.value = '登录成功。'
    password.value = ''
    showDiagnosticButton.value = false
  } catch (error) {
    handleError(error, '登录失败，请检查邮箱和密码。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleRegister() {
  if (!email.value.trim() || !password.value) {
    errorMessage.value = '请输入邮箱和密码。'
    return
  }

  isSubmitting.value = true
  clearMessages()

  try {
    const status = await cloudRegister(
      email.value.trim(),
      password.value,
      displayName.value.trim(),
    )
    accountStatus.value = status
    isLoggedIn.value = true
    cloudAvailable.value = status.cloud_available
    successMessage.value = '注册成功，已自动登录。'
    password.value = ''
    showDiagnosticButton.value = false
  } catch (error) {
    handleError(error, '注册失败，请稍后重试。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleLogout() {
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

function switchTab(tab: 'login' | 'register') {
  activeTab.value = tab
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
              <p class="info-email">{{ accountStatus?.email ?? accountStatus?.display_name }}</p>
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
              <label>
                <span>邮箱</span>
                <input v-model.trim="email" type="email" required placeholder="your@email.com" />
              </label>

              <label v-if="activeTab === 'register'">
                <span>显示名称</span>
                <input v-model.trim="displayName" type="text" placeholder="可选" />
              </label>

              <label>
                <span>密码</span>
                <input v-model="password" type="password" required />
                <span v-if="activeTab === 'register'" class="field-hint">
                  至少 10 个字符，建议包含字母和数字
                </span>
              </label>

              <button
                class="primary-button"
                type="submit"
                :disabled="isSubmitting || !email.trim() || !password"
              >
                {{
                  isSubmitting
                    ? activeTab === 'login'
                      ? '正在登录…'
                      : '正在注册…'
                    : activeTab === 'login'
                      ? '登录'
                      : '注册'
                }}
              </button>
            </form>
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
                {{ isSwitchingMode ? '正在切换...' : MODE_LABELS[diagnosticReport!.recommended_mode] }}
              </button>
            </div>

            <ul class="diagnostic-steps">
              <li v-for="step in diagnosticReport.steps.filter(s => !s.ok)" :key="step.name">
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
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
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

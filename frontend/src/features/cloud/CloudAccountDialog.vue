<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  cloudLogin,
  cloudLogout,
  cloudRegister,
  getCloudAccountStatus,
  runCloudNetworkDiagnostics,
} from '@/entities/cloud/api'
import type { CloudAccountStatus, CloudNetworkDiagnosticReport } from '@/entities/cloud/types'

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
const successMessage = ref('')

const accountStatus = ref<CloudAccountStatus | null>(null)

const isLoggedIn = ref(false)
const cloudAvailable = ref(false)
const showDiagnosticButton = ref(false)
const diagnosticReport = ref<CloudNetworkDiagnosticReport | null>(null)
const isDiagnosing = ref(false)

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
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const status = await cloudLogin(email.value.trim(), password.value)
    accountStatus.value = status
    isLoggedIn.value = true
    cloudAvailable.value = status.cloud_available
    successMessage.value = '登录成功。'
    password.value = ''
    showDiagnosticButton.value = false
  } catch (error) {
    const msg = getErrorMessage(error, '登录失败，请检查邮箱和密码。')
    errorMessage.value = msg
    // Show diagnostic button for network errors (not 401 auth errors)
    showDiagnosticButton.value = !isAuthError(error)
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
  errorMessage.value = ''
  successMessage.value = ''

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
    const msg = getErrorMessage(error, '注册失败，请稍后重试。')
    errorMessage.value = msg
    showDiagnosticButton.value = !isAuthError(error)
  } finally {
    isSubmitting.value = false
  }
}

async function handleLogout() {
  isSubmitting.value = true
  errorMessage.value = ''
  successMessage.value = ''

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
  errorMessage.value = ''
  successMessage.value = ''
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function isAuthError(error: unknown): boolean {
  // 401 errors are account/password errors, not network issues
  if (error instanceof Error && error.message) {
    const msg = error.message.toLowerCase()
    return msg.includes('401') || msg.includes('邮箱或密码错误') || msg.includes('密码错误')
  }
  return false
}

async function handleRunDiagnostics() {
  isDiagnosing.value = true
  diagnosticReport.value = null

  try {
    diagnosticReport.value = await runCloudNetworkDiagnostics()
  } catch {
    errorMessage.value = '诊断请求失败。'
  } finally {
    isDiagnosing.value = false
  }
}
</script>

<template>
  <div class="zs-dialog" @click.self="emit('close')">
    <div class="zs-dialog-content cloud-account-dialog">
      <header class="dialog-header">
        <h2>章枢云账户</h2>
        <button class="close-button" type="button" @click="emit('close')">×</button>
      </header>

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
</template>

<style scoped>
.cloud-account-dialog {
  max-width: min(440px, calc(100vw - 32px));
  display: grid;
  gap: var(--zs-space-4);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  padding-bottom: var(--zs-space-3);
  border-bottom: 1px solid var(--zs-color-border-soft);
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
</style>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  bindCloudEmail,
  bindCloudPhone,
  getCloudAccountProfile,
  sendCloudBindEmailCode,
  sendCloudBindPhoneCode,
} from '@/entities/cloud/api'
import type { CloudAccountProfile } from '@/entities/cloud/types'
import CloudPasswordChangePanel from './CloudPasswordChangePanel.vue'

const router = useRouter()

const profile = ref<CloudAccountProfile | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const emailToBind = ref('')
const emailCode = ref('')
const phoneToBind = ref('')
const phoneCode = ref('')
const isSendingEmailCode = ref(false)
const isSendingPhoneCode = ref(false)
const isBindingEmail = ref(false)
const isBindingPhone = ref(false)
const emailCooldown = ref(0)
const phoneCooldown = ref(0)

let cooldownTimer: ReturnType<typeof setInterval> | null = null

const hasEmail = computed(() => Boolean(profile.value?.email))
const hasPhone = computed(() => Boolean(profile.value?.phone_number))

onMounted(async () => {
  await loadProfile()
})

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

async function loadProfile() {
  try {
    profile.value = await getCloudAccountProfile()
  } catch {
    errorMessage.value = '无法加载账户信息。'
  } finally {
    loading.value = false
  }
}

function handlePasswordSuccess() {
  router.push('/projects')
}

function handleError(msg: string) {
  errorMessage.value = msg
  setTimeout(() => {
    errorMessage.value = ''
  }, 5000)
}

function showSuccess(msg: string) {
  successMessage.value = msg
  setTimeout(() => {
    successMessage.value = ''
  }, 4000)
}

function clearMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

function startCooldown(kind: 'email' | 'phone', seconds: number) {
  if (kind === 'email') {
    emailCooldown.value = seconds
  } else {
    phoneCooldown.value = seconds
  }

  if (cooldownTimer) return

  cooldownTimer = setInterval(() => {
    if (emailCooldown.value > 0) emailCooldown.value -= 1
    if (phoneCooldown.value > 0) phoneCooldown.value -= 1
    if (emailCooldown.value <= 0 && phoneCooldown.value <= 0 && cooldownTimer) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

async function handleSendEmailCode() {
  if (!emailToBind.value.trim()) {
    handleError('请输入要绑定的邮箱。')
    return
  }

  isSendingEmailCode.value = true
  clearMessages()
  try {
    const result = await sendCloudBindEmailCode(emailToBind.value.trim())
    startCooldown('email', result.cooldown_seconds)
    showSuccess('验证码已发送，请查看邮箱。')
  } catch (error) {
    handleError(errorText(error, '验证码发送失败，请稍后重试。'))
  } finally {
    isSendingEmailCode.value = false
  }
}

async function handleBindEmail() {
  if (!emailToBind.value.trim() || !emailCode.value.trim()) {
    handleError('请输入邮箱和验证码。')
    return
  }

  isBindingEmail.value = true
  clearMessages()
  try {
    profile.value = await bindCloudEmail(emailToBind.value.trim(), emailCode.value.trim())
    emailToBind.value = ''
    emailCode.value = ''
    showSuccess('邮箱已绑定。')
  } catch (error) {
    handleError(errorText(error, '邮箱绑定失败，请检查验证码。'))
  } finally {
    isBindingEmail.value = false
  }
}

async function handleSendPhoneCode() {
  if (!phoneToBind.value.trim()) {
    handleError('请输入要绑定的手机号。')
    return
  }

  isSendingPhoneCode.value = true
  clearMessages()
  try {
    const result = await sendCloudBindPhoneCode(phoneToBind.value.trim())
    startCooldown('phone', result.cooldown_seconds)
    showSuccess('验证码已发送，请查看手机。')
  } catch (error) {
    handleError(errorText(error, '验证码发送失败，请稍后重试。'))
  } finally {
    isSendingPhoneCode.value = false
  }
}

async function handleBindPhone() {
  if (!phoneToBind.value.trim() || !phoneCode.value.trim()) {
    handleError('请输入手机号和验证码。')
    return
  }

  isBindingPhone.value = true
  clearMessages()
  try {
    profile.value = await bindCloudPhone(phoneToBind.value.trim(), phoneCode.value.trim())
    phoneToBind.value = ''
    phoneCode.value = ''
    showSuccess('手机号已绑定。')
  } catch (error) {
    handleError(errorText(error, '手机号绑定失败，请检查验证码。'))
  } finally {
    isBindingPhone.value = false
  }
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleDateString('zh-CN')
  } catch {
    return d
  }
}
</script>

<template>
  <div class="security-page">
    <header class="page-header">
      <button class="btn-back" @click="router.push('/account')">&larr; 返回账户</button>
      <h1 class="page-title">账号安全</h1>
    </header>

    <p v-if="loading" class="loading-text">加载中...</p>

    <template v-else>
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

      <section class="card identity-section" v-if="profile">
        <h2 class="section-title">登录方式</h2>
        <div class="info-row">
          <span class="info-label">邮箱</span>
          <span :class="['info-value', { muted: !hasEmail }]">
            {{ profile.email || '未绑定' }}
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">手机号</span>
          <span :class="['info-value', { muted: !hasPhone }]">
            {{ profile.phone_number || '未绑定' }}
          </span>
        </div>
      </section>

      <section v-if="profile && !hasEmail" class="card bind-section">
        <h2 class="section-title">绑定邮箱</h2>
        <form class="bind-form" @submit.prevent="handleBindEmail">
          <label class="field">
            <span>邮箱</span>
            <input v-model.trim="emailToBind" type="email" required placeholder="your@email.com" />
          </label>
          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input v-model.trim="emailCode" inputmode="numeric" maxlength="10" required />
              <button
                class="btn-secondary code-button"
                type="button"
                :disabled="isSendingEmailCode || !emailToBind.trim() || emailCooldown > 0"
                @click="handleSendEmailCode"
              >
                {{
                  emailCooldown > 0
                    ? `${emailCooldown}s`
                    : isSendingEmailCode
                      ? '发送中…'
                      : '发送验证码'
                }}
              </button>
            </div>
          </label>
          <button
            class="btn-primary"
            type="submit"
            :disabled="isBindingEmail || !emailToBind.trim() || !emailCode.trim()"
          >
            {{ isBindingEmail ? '绑定中…' : '绑定邮箱' }}
          </button>
        </form>
      </section>

      <section v-if="profile && !hasPhone" class="card bind-section">
        <h2 class="section-title">绑定手机号</h2>
        <form class="bind-form" @submit.prevent="handleBindPhone">
          <label class="field">
            <span>手机号</span>
            <input v-model.trim="phoneToBind" inputmode="tel" required placeholder="13800138000" />
          </label>
          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input v-model.trim="phoneCode" inputmode="numeric" maxlength="10" required />
              <button
                class="btn-secondary code-button"
                type="button"
                :disabled="isSendingPhoneCode || !phoneToBind.trim() || phoneCooldown > 0"
                @click="handleSendPhoneCode"
              >
                {{
                  phoneCooldown > 0
                    ? `${phoneCooldown}s`
                    : isSendingPhoneCode
                      ? '发送中…'
                      : '发送验证码'
                }}
              </button>
            </div>
          </label>
          <button
            class="btn-primary"
            type="submit"
            :disabled="isBindingPhone || !phoneToBind.trim() || !phoneCode.trim()"
          >
            {{ isBindingPhone ? '绑定中…' : '绑定手机号' }}
          </button>
        </form>
      </section>

      <section class="card password-info-section">
        <h2 class="section-title">密码</h2>
        <div class="info-row">
          <span class="info-label">修改时间</span>
          <span class="info-value">{{ formatDate(profile?.password_changed_at ?? null) }}</span>
        </div>
      </section>

      <section class="card password-change-section">
        <CloudPasswordChangePanel
          @success="handlePasswordSuccess"
          @error="handleError"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.security-page {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--zs-space-5);
}

.page-header {
  margin-bottom: var(--zs-space-5);
}

.btn-back {
  padding: var(--zs-space-2) 0;
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  margin-bottom: var(--zs-space-2);
}

.btn-back:hover {
  color: var(--zs-color-primary);
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.loading-text {
  color: var(--zs-color-text-muted);
  text-align: center;
  padding: var(--zs-space-6);
}

.message {
  padding: var(--zs-space-3) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  margin-bottom: var(--zs-space-4);
  font-size: 0.9rem;
}

.message-error {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
}

.message-success {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success);
}

.card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4) var(--zs-space-5);
  margin-bottom: var(--zs-space-4);
}

.section-title {
  margin: 0 0 var(--zs-space-3);
  font-size: 1rem;
  font-weight: 700;
}

.identity-section,
.password-info-section {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--zs-space-2) 0;
  gap: var(--zs-space-3);
}

.info-label {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.info-value {
  font-weight: 500;
  font-size: 0.9rem;
  overflow-wrap: anywhere;
  text-align: right;
}

.info-value.muted {
  color: var(--zs-color-text-muted);
  font-weight: 400;
}

.bind-section {
  display: grid;
  gap: var(--zs-space-3);
}

.bind-form {
  display: grid;
  gap: var(--zs-space-3);
}

.field {
  display: grid;
  gap: var(--zs-space-2);
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  font-weight: 600;
}

.field input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.field input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
}

.code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--zs-space-2);
  align-items: center;
}

.code-button {
  min-width: 112px;
  white-space: nowrap;
}

.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-3);
  border: 1px solid transparent;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  justify-self: start;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.btn-secondary {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 520px) {
  .security-page {
    padding-inline: var(--zs-space-4);
  }

  .code-row {
    grid-template-columns: 1fr;
  }

  .code-button {
    width: 100%;
  }
}
</style>

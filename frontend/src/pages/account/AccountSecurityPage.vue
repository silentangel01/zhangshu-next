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
      <div class="page-heading">
        <p class="page-kicker">章枢 · 账户档案</p>
        <h1 class="page-title">账号安全</h1>
        <p class="page-subtitle">集中维护登录凭证、绑定方式与密码状态。</p>
      </div>
    </header>

    <section v-if="loading" class="loading-card">
      <span class="loading-index">安全档案 · 读取中</span>
      <div class="loading-copy">
        <span class="loading-dot" aria-hidden="true" />
        <div>
          <strong>正在载入安全信息</strong>
          <p>正在核验登录方式和密码状态…</p>
        </div>
      </div>
    </section>

    <template v-else>
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

      <div class="security-layout">
        <aside class="security-overview">
          <div class="overview-header">
            <span class="overview-index">安全档案 · 01</span>
            <span class="overview-state">{{ profile ? '资料已载入' : '本地校验' }}</span>
          </div>

          <div class="overview-copy">
            <p class="overview-label">账户保护</p>
            <h2>登录凭证概览</h2>
            <p>绑定多种登录方式，可以在更换设备或忘记密码时更稳妥地找回账户。</p>
          </div>

          <section v-if="profile" class="overview-block">
            <h3>登录方式</h3>
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

          <section class="overview-block">
            <h3>密码记录</h3>
            <div class="info-row">
              <span class="info-label">最近修改</span>
              <span class="info-value">{{ formatDate(profile?.password_changed_at ?? null) }}</span>
            </div>
          </section>

          <p class="security-note">密码修改后，所有已登录设备都需要重新验证身份。</p>
        </aside>

        <div class="security-actions">
          <section v-if="profile && !hasEmail" class="card bind-section">
            <p class="section-index">01 · 补全登录方式</p>
            <h2 class="section-title">绑定邮箱</h2>
            <p class="section-desc">用于接收验证码和恢复账户访问。</p>
            <form class="bind-form" @submit.prevent="handleBindEmail">
              <label class="field">
                <span>邮箱</span>
                <input
                  v-model.trim="emailToBind"
                  type="email"
                  required
                  placeholder="your@email.com"
                />
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
            <p class="section-index">02 · 补全登录方式</p>
            <h2 class="section-title">绑定手机号</h2>
            <p class="section-desc">增加一种独立的账户验证方式。</p>
            <form class="bind-form" @submit.prevent="handleBindPhone">
              <label class="field">
                <span>手机号</span>
                <input
                  v-model.trim="phoneToBind"
                  inputmode="tel"
                  required
                  placeholder="13800138000"
                />
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

          <section class="card password-change-section">
            <p class="section-index">03 · 密码凭证</p>
            <CloudPasswordChangePanel @success="handlePasswordSuccess" @error="handleError" />
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.security-page {
  width: 100%;
  max-width: 1180px;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 36px 40px 64px;
}

.page-header {
  display: grid;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-6);
  padding-bottom: var(--zs-space-5);
  border-bottom: 1px solid var(--zs-color-border);
}

.btn-back {
  justify-self: start;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-back:hover {
  color: var(--zs-color-primary);
}

.page-heading {
  display: grid;
  gap: var(--zs-space-1);
}

.page-kicker,
.page-subtitle {
  margin: 0;
}

.page-kicker,
.section-index,
.overview-index {
  color: var(--zs-color-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.page-title {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.page-subtitle {
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
}

.loading-card {
  display: grid;
  min-height: 280px;
  box-sizing: border-box;
  align-content: center;
  gap: var(--zs-space-6);
  padding: 44px 48px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
}

.loading-index {
  color: var(--zs-color-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.loading-copy {
  display: flex;
  align-items: center;
  gap: var(--zs-space-4);
}

.loading-copy strong {
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.2rem;
}

.loading-copy p {
  margin: 6px 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
}

.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--zs-color-primary);
  box-shadow: 0 0 0 7px color-mix(in srgb, var(--zs-color-primary) 12%, transparent);
  animation: security-pulse 1.4s ease-in-out infinite;
}

.message {
  width: 100%;
  box-sizing: border-box;
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

.security-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.78fr) minmax(0, 1.72fr);
  gap: var(--zs-space-6);
  align-items: start;
}

.security-overview {
  position: sticky;
  top: var(--zs-space-6);
  display: flex;
  flex-direction: column;
  min-height: 520px;
  box-sizing: border-box;
  overflow: hidden;
  padding: var(--zs-space-5);
  border: 1px solid var(--zs-color-border);
  border-top: 3px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-md);
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--zs-color-primary) 8%, transparent),
      transparent 48%
    ),
    var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
}

.overview-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-success);
  font-size: 0.72rem;
  font-weight: 700;
}

.overview-state::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.overview-copy {
  margin: var(--zs-space-7) 0 var(--zs-space-5);
}

.overview-label {
  margin: 0 0 var(--zs-space-2);
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.overview-copy h2 {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.35rem;
}

.overview-copy > p:last-child {
  margin: var(--zs-space-3) 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.7;
}

.overview-block {
  padding: var(--zs-space-4) 0;
  border-top: 1px solid var(--zs-color-border-soft);
}

.overview-block h3 {
  margin: 0 0 var(--zs-space-2);
  font-size: 0.82rem;
  font-weight: 700;
}

.security-note {
  margin: auto 0 0;
  padding-top: var(--zs-space-5);
  border-top: 1px solid var(--zs-color-border-soft);
  color: var(--zs-color-text-faint);
  font-size: 0.76rem;
  line-height: 1.65;
}

.security-actions {
  display: grid;
  gap: var(--zs-space-4);
}

.card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 28px 30px;
  box-shadow: var(--zs-shadow-sm);
}

.section-index {
  margin: 0 0 6px;
}

.section-title {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.2rem;
  font-weight: 700;
}

.section-desc {
  margin: var(--zs-space-2) 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.6;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 0;
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
  gap: var(--zs-space-1);
}

.bind-form {
  display: grid;
  gap: var(--zs-space-3);
  max-width: 620px;
  margin-top: var(--zs-space-4);
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

.password-change-section :deep(.panel-title) {
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.2rem;
}

.password-change-section :deep(form) {
  max-width: 620px;
  margin-top: var(--zs-space-2);
}

@keyframes security-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-dot {
    animation: none;
  }
}

@media (max-width: 900px) {
  .security-page {
    padding-right: var(--zs-space-6);
    padding-left: var(--zs-space-6);
  }

  .security-layout {
    grid-template-columns: 1fr;
  }

  .security-overview {
    position: relative;
    top: auto;
    min-height: 0;
  }

  .security-note {
    margin-top: var(--zs-space-4);
  }
}

@media (max-width: 640px) {
  .security-page {
    padding: var(--zs-space-5) var(--zs-space-3) var(--zs-space-8);
  }

  .page-title {
    font-size: 1.65rem;
  }

  .card,
  .loading-card {
    padding: var(--zs-space-5);
  }

  .code-row {
    grid-template-columns: 1fr;
  }

  .code-button {
    width: 100%;
  }
}
</style>

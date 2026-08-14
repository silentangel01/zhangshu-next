<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import {
  cloudLogout,
} from '@/entities/cloud/api'
import { useCloudAccountStore } from '@/stores/cloudAccount'
import CloudAvatarUploader from './CloudAvatarUploader.vue'
import CloudSignatureEditor from './CloudSignatureEditor.vue'
import AppVersionPanel from './AppVersionPanel.vue'

const router = useRouter()
const cloudAccountStore = useCloudAccountStore()
const {
  profile,
  usage,
  status,
  hydrated,
  sessionState,
  lastError,
} = storeToRefs(cloudAccountStore)
const loading = computed(() => !hydrated.value)
const isLoggedIn = computed(() => status.value?.logged_in ?? false)
const cloudAvailable = computed(() => status.value?.cloud_available ?? false)
const tokenExpired = computed(() => sessionState.value === 'expired')
const errorMessage = ref('')
const successMessage = ref('')

const accountIdentifier = computed(() => {
  if (!profile.value) return ''
  return profile.value.email || profile.value.phone_number || '未绑定登录方式'
})

const storageUsagePercent = computed(() => {
  if (!usage.value || usage.value.storage_quota_bytes <= 0) return 0
  return Math.min(100, (usage.value.storage_used_bytes / usage.value.storage_quota_bytes) * 100)
})

const backupUsagePercent = computed(() => {
  if (!usage.value || usage.value.backup_count_quota <= 0) return 0
  return Math.min(100, (usage.value.backup_count / usage.value.backup_count_quota) * 100)
})

onMounted(async () => {
  await cloudAccountStore.hydrate()
  if (isLoggedIn.value) {
    void loadProfile()
  }
})

async function loadProfile() {
  await cloudAccountStore.refresh()
  if (sessionState.value === 'expired') {
    errorMessage.value = '登录已过期，请重新登录。'
  } else if (lastError.value) {
    errorMessage.value = lastError.value
  }
}

function handleAvatarUpdated() {
  loadProfile()
  showSuccess('头像已更新。')
}

function handleSignatureUpdated() {
  loadProfile()
  showSuccess('签名已保存。')
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
  }, 3000)
}

async function handleLogout() {
  try {
    await cloudLogout()
  } catch {
    // Logout API may fail if backend is unreachable — that's OK,
    // the backend logout endpoint only clears local tokens.
  }
  cloudAccountStore.clear()
  router.push('/projects')
}

function openLoginDialog() {
  // Navigate to projects page with query param to auto-open login dialog
  router.push('/projects?openCloudDialog=1')
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleDateString('zh-CN')
  } catch {
    return d
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
</script>

<template>
  <div class="profile-page">
    <header class="page-header">
      <RouterLink class="back-link" to="/projects">← 返回项目列表</RouterLink>
      <div class="page-heading">
        <p class="page-kicker">章枢 · 账户档案</p>
        <h1 class="page-title">个人账户</h1>
        <p class="page-subtitle">管理你的身份、云端容量与客户端状态。</p>
      </div>
    </header>

    <div v-if="loading" class="account-state-layout">
      <aside class="state-aside">
        <div class="state-aside-header">
          <span class="state-index">账户状态 · 读取中</span>
          <span class="state-status">正在检查</span>
        </div>
        <div class="state-aside-copy">
          <p>云端连接</p>
          <h2>核验账户身份</h2>
          <span>正在读取登录状态、云端容量与客户端信息。</span>
        </div>
        <p class="state-aside-note">账户资料仅用于章枢云同步、备份和反馈服务。</p>
      </aside>

      <section class="loading-state" aria-live="polite">
        <span class="state-card-index">连接检查</span>
        <div class="state-card-copy">
          <span class="state-loading-dot" aria-hidden="true" />
          <div>
            <p class="empty-title">正在载入账户信息</p>
            <p class="empty-desc">正在核验云端身份与本机登录凭证…</p>
          </div>
        </div>
      </section>
    </div>

    <template v-else>
      <!-- Messages -->
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

      <!-- Not logged in state -->
      <div v-if="!isLoggedIn" class="account-state-layout">
        <aside class="state-aside">
          <div class="state-aside-header">
            <span class="state-index">账户状态 · 尚未连接</span>
            <span class="state-status">{{ cloudAvailable ? '可以登录' : '等待配置' }}</span>
          </div>
          <div class="state-aside-copy">
            <p>云端连接</p>
            <h2>连接章枢账户</h2>
            <span>登录后，作品备份、同步记录和反馈历史会关联到同一身份。</span>
          </div>
          <p class="state-aside-note">本地写作功能不受登录状态影响。</p>
        </aside>

        <section class="empty-card">
          <span class="state-card-index">身份验证</span>
          <p class="empty-title">{{ cloudAvailable ? '尚未登录云账户' : '云服务暂未配置' }}</p>
          <p class="empty-desc">
            {{
              cloudAvailable
                ? '登录后可使用云备份、云同步等功能。'
                : '请在后端配置云服务后使用账户功能。'
            }}
          </p>
          <button v-if="cloudAvailable" class="btn-primary" @click="openLoginDialog">
            登录 / 注册
          </button>
        </section>
      </div>

      <!-- Token expired state -->
      <div v-else-if="tokenExpired" class="account-state-layout">
        <aside class="state-aside state-aside-warning">
          <div class="state-aside-header">
            <span class="state-index">账户状态 · 凭证失效</span>
            <span class="state-status">需要处理</span>
          </div>
          <div class="state-aside-copy">
            <p>连接恢复</p>
            <h2>重新验证身份</h2>
            <span>本机保存的登录凭证已经失效，云端数据不会因此被删除。</span>
          </div>
          <p class="state-aside-note">重新登录后即可继续访问云同步和备份记录。</p>
        </aside>

        <section class="empty-card">
          <span class="state-card-index">身份验证</span>
          <p class="empty-title">登录已过期</p>
          <p class="empty-desc">请重新登录以继续使用云功能。</p>
          <div class="empty-actions">
            <button class="btn-primary" @click="openLoginDialog">重新登录</button>
            <button class="btn-secondary" @click="handleLogout">退出登录</button>
          </div>
        </section>
      </div>

      <!-- Logged in state -->
      <template v-else-if="profile">
        <div class="profile-layout">
          <aside class="identity-card">
            <div class="identity-card-header">
              <span class="identity-index">账户档案 · 01</span>
              <span class="identity-state">云端已连接</span>
            </div>

            <CloudAvatarUploader
              :profile="profile"
              @updated="handleAvatarUpdated"
              @error="handleError"
            />

            <div class="profile-info">
              <p class="identity-label">章枢身份</p>
              <h2 class="display-name">{{ profile.display_name || '章枢用户' }}</h2>
              <p class="email">{{ accountIdentifier }}</p>
            </div>

            <div class="identity-note">此账户用于关联作品云同步、备份记录和意见反馈。</div>

            <div class="identity-footer">
              <span>建立于 {{ formatDate(profile.created_at) }}</span>
              <button class="btn-secondary btn-logout" @click="handleLogout">退出登录</button>
            </div>
          </aside>

          <div class="account-sheet">
            <section class="sheet-section overview-section">
              <div class="section-heading-row">
                <div>
                  <p class="section-index">01 · 云端概览</p>
                  <h2 class="sheet-title">使用情况</h2>
                </div>
                <span class="connection-badge">连接正常</span>
              </div>

              <div class="usage-grid">
                <article class="usage-metric">
                  <span class="metric-label">加入章枢</span>
                  <strong class="metric-value">{{ formatDate(profile.created_at) }}</strong>
                  <span class="metric-note">账户建立时间</span>
                </article>

                <article v-if="usage" class="usage-metric">
                  <span class="metric-label">云存储</span>
                  <strong class="metric-value">
                    {{ formatBytes(usage.storage_used_bytes) }}
                  </strong>
                  <span class="metric-note">共 {{ formatBytes(usage.storage_quota_bytes) }}</span>
                  <div class="usage-track" aria-hidden="true">
                    <span :style="{ width: `${storageUsagePercent}%` }" />
                  </div>
                </article>

                <article v-if="usage" class="usage-metric">
                  <span class="metric-label">云备份</span>
                  <strong class="metric-value">{{ usage.backup_count }} 份</strong>
                  <span class="metric-note">上限 {{ usage.backup_count_quota }} 份</span>
                  <div class="usage-track" aria-hidden="true">
                    <span :style="{ width: `${backupUsagePercent}%` }" />
                  </div>
                </article>
              </div>
            </section>

            <section class="sheet-section signature-section">
              <p class="section-index">02 · 个人表达</p>
              <CloudSignatureEditor
                :signature="profile.signature"
                @updated="handleSignatureUpdated"
                @error="handleError"
              />
            </section>

            <div class="action-grid">
              <section class="action-section security-section">
                <span class="action-number">03</span>
                <div>
                  <h3 class="section-title">账号安全</h3>
                  <p class="section-desc">维护密码与登录安全。</p>
                </div>
                <RouterLink to="/account/security" class="btn-secondary">管理安全设置</RouterLink>
              </section>

              <section class="action-section feedback-section">
                <span class="action-number">04</span>
                <div>
                  <h3 class="section-title">我的反馈</h3>
                  <p class="section-desc">查看反馈进度与管理员回复。</p>
                </div>
                <RouterLink to="/account/feedback" class="btn-secondary">查看反馈历史</RouterLink>
              </section>
            </div>

            <section class="sheet-section version-section">
              <p class="section-index">05 · 客户端</p>
              <AppVersionPanel />
            </section>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
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

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-weight: 600;
  text-decoration: none;
}

.back-link:hover {
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

.page-kicker {
  color: var(--zs-color-accent);
  font-family: Georgia, 'Songti SC', serif;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
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

.loading-state {
  display: grid;
  min-height: 310px;
  box-sizing: border-box;
  align-content: center;
  gap: var(--zs-space-6);
  padding: 44px 48px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.88rem;
  box-shadow: var(--zs-shadow-sm);
}

.account-state-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.78fr) minmax(0, 1.72fr);
  gap: var(--zs-space-6);
  align-items: stretch;
}

.state-aside {
  display: flex;
  flex-direction: column;
  min-height: 310px;
  box-sizing: border-box;
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

.state-aside-warning {
  border-top-color: var(--zs-color-danger);
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--zs-color-danger) 7%, transparent),
      transparent 48%
    ),
    var(--zs-color-surface);
}

.state-aside-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
}

.state-index,
.state-card-index {
  color: var(--zs-color-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.state-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-success);
  font-size: 0.72rem;
  font-weight: 700;
}

.state-aside-warning .state-status {
  color: var(--zs-color-danger);
}

.state-status::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.state-aside-copy {
  margin-top: var(--zs-space-7);
}

.state-aside-copy p {
  margin: 0 0 var(--zs-space-2);
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.state-aside-copy h2 {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.35rem;
}

.state-aside-copy span {
  display: block;
  margin-top: var(--zs-space-3);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.7;
}

.state-aside-note {
  margin: auto 0 0;
  padding-top: var(--zs-space-5);
  border-top: 1px solid var(--zs-color-border-soft);
  color: var(--zs-color-text-faint);
  font-size: 0.76rem;
  line-height: 1.65;
}

.state-card-copy {
  display: flex;
  align-items: center;
  gap: var(--zs-space-4);
}

.state-loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--zs-color-primary);
  box-shadow: 0 0 0 7px color-mix(in srgb, var(--zs-color-primary) 12%, transparent);
  animation: account-state-pulse 1.4s ease-in-out infinite;
}

.message {
  width: 100%;
  box-sizing: border-box;
  padding: var(--zs-space-2) var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  margin-bottom: var(--zs-space-3);
  font-size: 0.84rem;
  font-weight: 600;
}

.message-error {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
}

.message-success {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success);
}

.empty-card {
  display: grid;
  gap: var(--zs-space-2);
  min-height: 310px;
  box-sizing: border-box;
  align-content: center;
  justify-items: start;
  padding: 44px 48px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.empty-title {
  margin: 0;
  color: var(--zs-color-text);
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.25rem;
  font-weight: 600;
}

.empty-desc {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  line-height: 1.6;
}

.empty-actions {
  display: flex;
  gap: var(--zs-space-2);
  margin-top: var(--zs-space-4);
}

.profile-layout {
  display: grid;
  grid-template-columns: minmax(290px, 0.78fr) minmax(0, 1.72fr);
  gap: var(--zs-space-6);
  align-items: start;
}

.identity-card {
  position: sticky;
  top: var(--zs-space-6);
  display: flex;
  flex-direction: column;
  min-height: 560px;
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

.identity-card::after {
  position: absolute;
  right: -72px;
  bottom: 72px;
  width: 180px;
  height: 180px;
  border: 1px solid color-mix(in srgb, var(--zs-color-primary) 16%, transparent);
  border-radius: 50%;
  content: '';
  pointer-events: none;
}

.identity-card > * {
  position: relative;
  z-index: 1;
}

.identity-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  margin-bottom: var(--zs-space-6);
}

.identity-index,
.identity-state {
  font-size: 0.72rem;
  font-weight: 700;
}

.identity-index {
  color: var(--zs-color-accent);
  letter-spacing: 0.08em;
}

.identity-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-success);
}

.identity-state::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.identity-card :deep(.avatar-uploader) {
  align-items: flex-start;
}

.identity-card :deep(.avatar-preview) {
  width: 112px;
  height: 112px;
}

.identity-card :deep(.avatar-actions) {
  justify-content: flex-start;
}

.identity-card :deep(.avatar-hint) {
  text-align: left;
}

.profile-info {
  margin-top: var(--zs-space-6);
  padding-top: var(--zs-space-5);
  border-top: 1px solid var(--zs-color-border-soft);
}

.identity-label {
  margin: 0 0 var(--zs-space-2);
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.display-name {
  margin: 0 0 6px;
  overflow-wrap: anywhere;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.45rem;
  font-weight: 700;
}

.email {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
}

.identity-note {
  margin-top: var(--zs-space-5);
  padding: var(--zs-space-3) 0;
  border-top: 1px solid var(--zs-color-border-soft);
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.7;
}

.identity-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  margin-top: auto;
  padding-top: var(--zs-space-4);
  color: var(--zs-color-text-faint);
  font-size: 0.75rem;
}

.account-sheet {
  overflow: hidden;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.sheet-section {
  padding: 28px 30px;
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.sheet-section:last-child {
  border-bottom: 0;
}

.section-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-5);
}

.section-index {
  margin: 0 0 5px;
  color: var(--zs-color-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.sheet-title {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.25rem;
}

.connection-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 var(--zs-space-2);
  border: 1px solid color-mix(in srgb, var(--zs-color-success) 30%, transparent);
  border-radius: var(--zs-radius-pill);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
  font-size: 0.72rem;
  font-weight: 700;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.usage-metric {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 126px;
  padding: 0 var(--zs-space-5);
  border-left: 1px solid var(--zs-color-border-soft);
}

.usage-metric:first-child {
  padding-left: 0;
  border-left: 0;
}

.usage-metric:last-child {
  padding-right: 0;
}

.metric-label,
.metric-note {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
}

.metric-value {
  margin: var(--zs-space-3) 0 4px;
  overflow-wrap: anywhere;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.25rem;
  font-weight: 700;
}

.usage-track {
  height: 3px;
  margin-top: auto;
  overflow: hidden;
  border-radius: var(--zs-radius-pill);
  background: var(--zs-color-surface-muted);
}

.usage-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--zs-color-primary);
  transition: width var(--zs-duration-slow) var(--zs-ease-emphasized);
}

.signature-section :deep(.field-label) {
  color: var(--zs-color-text);
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.05rem;
  font-weight: 700;
}

.signature-section :deep(.signature-input) {
  min-height: 112px;
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-canvas);
  line-height: 1.7;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.action-section {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--zs-space-4);
  min-height: 176px;
  padding: 28px 30px;
}

.action-section + .action-section {
  border-left: 1px solid var(--zs-color-border-soft);
}

.action-number {
  color: var(--zs-color-border-strong);
  font-family: Georgia, serif;
  font-size: 0.86rem;
}

.action-section .btn-secondary {
  grid-column: 2;
  justify-self: start;
  margin-top: auto;
}

.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  text-decoration: none;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.btn-primary {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.btn-primary:hover {
  background: var(--zs-color-primary-hover);
}

.btn-secondary {
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border-color: var(--zs-color-border);
}

.btn-secondary:hover {
  background: var(--zs-color-surface-soft);
  border-color: var(--zs-color-border-strong);
}

.btn-logout {
  min-width: auto;
  min-height: 30px;
  padding: 0 var(--zs-space-2);
  background: transparent;
  color: var(--zs-color-danger);
}

.section-title {
  margin: 0 0 6px;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.05rem;
  font-weight: 700;
}

.section-desc {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}

.version-section :deep(.version-panel) {
  padding: 0;
  border-radius: 0;
  background: transparent;
}

.version-section :deep(.version-row) {
  margin-top: var(--zs-space-3);
  padding-top: var(--zs-space-3);
  border-top: 1px solid var(--zs-color-border-soft);
}

@keyframes account-state-pulse {
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
  .state-loading-dot {
    animation: none;
  }
}

@media (max-width: 900px) {
  .profile-page {
    padding-right: var(--zs-space-6);
    padding-left: var(--zs-space-6);
  }

  .profile-layout {
    grid-template-columns: 1fr;
  }

  .account-state-layout {
    grid-template-columns: 1fr;
  }

  .state-aside {
    min-height: 0;
  }

  .state-aside-note {
    margin-top: var(--zs-space-5);
  }

  .identity-card {
    position: relative;
    top: auto;
    min-height: 0;
  }

  .identity-footer {
    margin-top: var(--zs-space-6);
  }
}

@media (max-width: 640px) {
  .profile-page {
    padding: var(--zs-space-5) var(--zs-space-3) var(--zs-space-8);
  }

  .page-title {
    font-size: 1.65rem;
  }

  .sheet-section,
  .action-section,
  .empty-card,
  .loading-state {
    padding: var(--zs-space-5);
  }

  .usage-grid,
  .action-grid {
    grid-template-columns: 1fr;
  }

  .usage-metric {
    min-height: 0;
    padding: var(--zs-space-4) 0;
    border-top: 1px solid var(--zs-color-border-soft);
    border-left: 0;
  }

  .usage-metric:first-child {
    padding-top: 0;
    border-top: 0;
  }

  .usage-track {
    margin-top: var(--zs-space-3);
  }

  .action-section + .action-section {
    border-top: 1px solid var(--zs-color-border-soft);
    border-left: 0;
  }

  .identity-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

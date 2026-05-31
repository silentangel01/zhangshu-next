<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getCloudAccountProfile,
  getCloudAccountStatus,
  getCloudUsage,
  cloudLogout,
} from '@/entities/cloud/api'
import type { CloudAccountProfile, CloudUsage } from '@/entities/cloud/types'
import CloudAvatarUploader from './CloudAvatarUploader.vue'
import CloudSignatureEditor from './CloudSignatureEditor.vue'
import AppVersionPanel from './AppVersionPanel.vue'

const router = useRouter()

const profile = ref<CloudAccountProfile | null>(null)
const usage = ref<CloudUsage | null>(null)
const loading = ref(true)
const isLoggedIn = ref(false)
const cloudAvailable = ref(false)
const tokenExpired = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

onMounted(async () => {
  try {
    const status = await getCloudAccountStatus()
    cloudAvailable.value = status.cloud_available
    isLoggedIn.value = status.logged_in

    if (status.logged_in) {
      await loadProfile()
    }
  } catch {
    errorMessage.value = '无法加载账户信息。'
  } finally {
    loading.value = false
  }
})

async function loadProfile() {
  try {
    const [profileResult, usageResult] = await Promise.all([
      getCloudAccountProfile(),
      getCloudUsage(),
    ])
    profile.value = profileResult
    usage.value = usageResult
  } catch (err: unknown) {
    const status = (err as { status?: number })?.status
    if (status === 401) {
      tokenExpired.value = true
      errorMessage.value = '登录已过期，请重新登录。'
    } else {
      errorMessage.value = '无法加载个人资料。'
    }
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
  isLoggedIn.value = false
  tokenExpired.value = false
  profile.value = null
  router.push('/projects')
}

function openLoginDialog() {
  // Emit event to parent or use router to open dialog
  // For now, redirect to projects page where user can open the dialog
  router.push('/projects')
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
      <button class="btn-back" @click="router.push('/projects')">&larr; 返回项目列表</button>
      <h1 class="page-title">个人账户</h1>
    </header>

    <p v-if="loading" class="loading-text">加载中...</p>

    <template v-else>
      <!-- Messages -->
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

      <!-- Not logged in state -->
      <div v-if="!isLoggedIn" class="not-logged-in">
        <p class="info-text">
          {{ cloudAvailable ? '您尚未登录云账户。' : '云服务暂未配置。' }}
        </p>
        <button v-if="cloudAvailable" class="btn-primary" @click="openLoginDialog">
          登录 / 注册
        </button>
      </div>

      <!-- Token expired state -->
      <div v-else-if="tokenExpired" class="token-expired">
        <p class="info-text">登录已过期，请重新登录。</p>
        <div class="expired-actions">
          <button class="btn-primary" @click="openLoginDialog">重新登录</button>
          <button class="btn-danger" @click="handleLogout">退出登录</button>
        </div>
      </div>

      <!-- Logged in state -->
      <template v-else-if="profile">
        <section class="card profile-section">
          <CloudAvatarUploader
            :profile="profile"
            @updated="handleAvatarUpdated"
            @error="handleError"
          />
          <div class="profile-info">
            <h2 class="display-name">{{ profile.display_name }}</h2>
            <p class="email">{{ profile.email }}</p>
          </div>
        </section>

        <section class="card info-section">
          <div class="info-row">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatDate(profile.created_at) }}</span>
          </div>
          <div v-if="usage" class="info-row">
            <span class="info-label">云存储用量</span>
            <span class="info-value">
              {{ formatBytes(usage.storage_used_bytes) }} / {{ formatBytes(usage.storage_quota_bytes) }}
            </span>
          </div>
          <div v-if="usage" class="info-row">
            <span class="info-label">云备份数</span>
            <span class="info-value">{{ usage.backup_count }} / {{ usage.backup_count_quota }}</span>
          </div>
        </section>

        <section class="card signature-section">
          <CloudSignatureEditor
            :signature="profile.signature"
            @updated="handleSignatureUpdated"
            @error="handleError"
          />
        </section>

        <section class="card security-section">
          <div class="security-row">
            <div>
              <h3 class="section-title">账号安全</h3>
              <p class="section-desc">修改密码</p>
            </div>
            <RouterLink to="/account/security" class="btn-secondary">
              管理
            </RouterLink>
          </div>
        </section>

        <section class="card version-section">
          <AppVersionPanel />
        </section>

        <section class="card feedback-section">
          <div class="feedback-row">
            <div>
              <h3 class="section-title">我的反馈</h3>
              <p class="section-desc">查看提交过的反馈和管理员回复</p>
            </div>
            <RouterLink to="/account/feedback" class="btn-secondary">
              查看反馈历史
            </RouterLink>
          </div>
        </section>

        <section class="card logout-section">
          <button class="btn-danger" @click="handleLogout">退出登录</button>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
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

.not-logged-in {
  text-align: center;
  padding: var(--zs-space-6);
}

.token-expired {
  text-align: center;
  padding: var(--zs-space-6);
}

.expired-actions {
  display: flex;
  gap: var(--zs-space-3);
  justify-content: center;
  margin-top: var(--zs-space-4);
}

.expired-actions .btn-danger {
  width: auto;
}

.info-text {
  color: var(--zs-color-text-muted);
  margin-bottom: var(--zs-space-4);
}

.card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4) var(--zs-space-5);
  margin-bottom: var(--zs-space-4);
}

.profile-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--zs-space-4);
}

.profile-info {
  text-align: center;
}

.display-name {
  margin: 0 0 var(--zs-space-1);
  font-size: 1.25rem;
  font-weight: 700;
}

.email {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--zs-space-2) 0;
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.info-value {
  font-weight: 500;
  font-size: 0.9rem;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.btn-secondary {
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border-color: var(--zs-color-border);
}

.btn-secondary:hover {
  background: var(--zs-color-surface-soft);
}

.btn-danger {
  background: var(--zs-color-danger);
  color: white;
  width: 100%;
}

.btn-danger:hover {
  opacity: 0.9;
}

.logout-section {
  margin-top: var(--zs-space-5);
}

.feedback-section {
  margin-top: var(--zs-space-4);
}

.security-section {
  margin-top: var(--zs-space-4);
}

.security-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feedback-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  margin: 0 0 var(--zs-space-1);
  font-size: 1rem;
  font-weight: 600;
}

.section-desc {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}
</style>

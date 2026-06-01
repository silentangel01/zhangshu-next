<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  changeCloudPassword,
  confirmCloudAccountDeletion,
  exportCloudAccountData,
  getCloudAccountProfile,
  requestCloudAccountDeletion,
  revokeAllCloudSessions,
  updateCloudAccountProfile,
} from '@/entities/cloud/api'
import type { CloudAccountProfile, CloudDeletionRequest } from '@/entities/cloud/types'

const emit = defineEmits<{
  (e: 'logged-out'): void
}>()

const isLoading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')

const profile = ref<CloudAccountProfile | null>(null)

// Edit display name
const isEditingName = ref(false)
const displayNameDraft = ref('')
const isSavingName = ref(false)

// Change password
const showPasswordForm = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isChangingPassword = ref(false)

// Delete account
const showDeleteSection = ref(false)
const deletePassword = ref('')
const isRequestingDeletion = ref(false)
const deletionRequest = ref<CloudDeletionRequest | null>(null)
const deletionConfirmText = ref('')
const isConfirmingDeletion = ref(false)

onMounted(async () => {
  try {
    profile.value = await getCloudAccountProfile()
  } catch {
    errorMessage.value = '加载账号信息失败。'
  } finally {
    isLoading.value = false
  }
})

async function handleUpdateDisplayName() {
  if (!displayNameDraft.value.trim()) {
    errorMessage.value = '显示名不能为空。'
    return
  }
  isSavingName.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const updated = await updateCloudAccountProfile({ display_name: displayNameDraft.value.trim() })
    profile.value = updated
    isEditingName.value = false
    successMessage.value = '显示名已更新。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '更新显示名失败。')
  } finally {
    isSavingName.value = false
  }
}

async function handleChangePassword() {
  errorMessage.value = ''
  successMessage.value = ''

  if (newPassword.value.length < 8) {
    errorMessage.value = '新密码至少需要 8 个字符。'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }

  isChangingPassword.value = true
  try {
    await changeCloudPassword(oldPassword.value, newPassword.value)
    successMessage.value = '密码已修改，请重新登录。'
    showPasswordForm.value = false
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    emit('logged-out')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '修改密码失败。')
  } finally {
    isChangingPassword.value = false
  }
}

async function handleRevokeAllSessions() {
  errorMessage.value = ''
  successMessage.value = ''

  if (!confirm('确定要退出所有设备吗？所有设备都需要重新登录。')) {
    return
  }

  try {
    const result = await revokeAllCloudSessions()
    successMessage.value = `已退出 ${result.revoked_count} 个会话，请重新登录。`
    emit('logged-out')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '退出所有设备失败。')
  }
}

async function handleExportData() {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const data = await exportCloudAccountData()
    const json = JSON.stringify(data, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `zhangshu-account-export-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    successMessage.value = '账号数据已导出。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '导出数据失败。')
  }
}

async function handleRequestDeletion() {
  errorMessage.value = ''
  successMessage.value = ''

  if (!deletePassword.value) {
    errorMessage.value = '请输入密码以确认删除。'
    return
  }

  isRequestingDeletion.value = true
  try {
    deletionRequest.value = await requestCloudAccountDeletion(deletePassword.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '发起删除请求失败。')
  } finally {
    isRequestingDeletion.value = false
  }
}

async function handleConfirmDeletion() {
  errorMessage.value = ''
  successMessage.value = ''

  if (!deletionRequest.value) return
  if (deletionConfirmText.value !== deletionRequest.value.confirmation_text) {
    errorMessage.value = `请输入确认文本：${deletionRequest.value.confirmation_text}`
    return
  }

  isConfirmingDeletion.value = true
  try {
    await confirmCloudAccountDeletion(
      deletionRequest.value.request_id,
      deletionConfirmText.value,
    )
    successMessage.value = '云账号已删除，本地作品数据不受影响。'
    emit('logged-out')
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除账号失败。')
  } finally {
    isConfirmingDeletion.value = false
  }
}

function startEditName() {
  displayNameDraft.value = profile.value?.display_name ?? ''
  isEditingName.value = true
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <article class="action-panel cloud-account-panel">
    <header>
      <p class="eyebrow">云账户</p>
      <h2>账户与隐私</h2>
    </header>
    <p class="panel-copy">
      管理你的章枢云账户。本地作品数据不会因云账户变动而删除。
    </p>

    <div v-if="isLoading" class="loading-state">正在加载…</div>

    <template v-else-if="profile">
      <!-- Profile section -->
      <section class="profile-section">
        <h3>账号信息</h3>
        <div class="profile-row">
          <span class="profile-label">邮箱</span>
          <span class="profile-value">{{ profile.email }}</span>
        </div>
        <div class="profile-row">
          <span class="profile-label">显示名</span>
          <template v-if="!isEditingName">
            <span class="profile-value">{{ profile.display_name || '未设置' }}</span>
            <button class="small-button" type="button" @click="startEditName">修改</button>
          </template>
          <template v-else>
            <input
              v-model="displayNameDraft"
              class="text-input"
              type="text"
              placeholder="输入新显示名"
            />
            <button
              class="small-button"
              type="button"
              :disabled="isSavingName"
              @click="handleUpdateDisplayName"
            >
              {{ isSavingName ? '保存中…' : '保存' }}
            </button>
            <button class="small-button ghost" type="button" @click="isEditingName = false">
              取消
            </button>
          </template>
        </div>
      </section>

      <!-- Password section -->
      <section class="action-section">
        <h3>安全</h3>
        <div class="action-row">
          <span class="action-label">修改密码</span>
          <button
            v-if="!showPasswordForm"
            class="small-button"
            type="button"
            @click="showPasswordForm = true"
          >
            修改密码
          </button>
        </div>
        <div v-if="showPasswordForm" class="password-form">
          <label class="form-field">
            <span>当前密码</span>
            <input v-model="oldPassword" class="text-input" type="password" />
          </label>
          <label class="form-field">
            <span>新密码</span>
            <input v-model="newPassword" class="text-input" type="password" />
          </label>
          <label class="form-field">
            <span>确认新密码</span>
            <input v-model="confirmPassword" class="text-input" type="password" />
          </label>
          <div class="form-actions">
            <button
              class="small-button"
              type="button"
              :disabled="isChangingPassword"
              @click="handleChangePassword"
            >
              {{ isChangingPassword ? '提交中…' : '确认修改' }}
            </button>
            <button class="small-button ghost" type="button" @click="showPasswordForm = false">
              取消
            </button>
          </div>
        </div>
        <div class="action-row">
          <span class="action-label">退出所有设备</span>
          <button class="small-button" type="button" @click="handleRevokeAllSessions">
            退出所有设备
          </button>
        </div>
      </section>

      <!-- Data export section -->
      <section class="action-section">
        <h3>数据</h3>
        <div class="action-row">
          <span class="action-label">导出账号数据（不含密码、Token）</span>
          <button class="small-button" type="button" @click="handleExportData">
            导出 JSON
          </button>
        </div>
      </section>

      <!-- Danger zone: delete account -->
      <section class="danger-section">
        <h3>危险区域</h3>
        <div class="action-row">
          <span class="action-label">删除云账号及所有云端备份（本地作品不受影响）</span>
          <button
            v-if="!showDeleteSection"
            class="danger-button"
            type="button"
            @click="showDeleteSection = true"
          >
            删除账号
          </button>
        </div>
        <div v-if="showDeleteSection" class="delete-form">
          <p class="warning-text">
            此操作将永久删除你的云账号和所有云端备份。本地作品数据不受影响。
          </p>
          <div v-if="!deletionRequest">
            <label class="form-field">
              <span>输入密码以继续</span>
              <input v-model="deletePassword" class="text-input" type="password" />
            </label>
            <button
              class="danger-button"
              type="button"
              :disabled="isRequestingDeletion"
              @click="handleRequestDeletion"
            >
              {{ isRequestingDeletion ? '验证中…' : '下一步：查看影响范围' }}
            </button>
          </div>
          <div v-else class="deletion-confirm">
            <p>将要删除：</p>
            <ul>
              <li>{{ deletionRequest.project_count }} 个项目</li>
              <li>{{ deletionRequest.backup_count }} 个备份</li>
              <li>总大小：{{ formatBytes(deletionRequest.total_size_bytes) }}</li>
            </ul>
            <label class="form-field">
              <span>输入 <code>{{ deletionRequest.confirmation_text }}</code> 以确认</span>
              <input v-model="deletionConfirmText" class="text-input" type="text" />
            </label>
            <button
              class="danger-button"
              type="button"
              :disabled="isConfirmingDeletion"
              @click="handleConfirmDeletion"
            >
              {{ isConfirmingDeletion ? '删除中…' : '确认删除' }}
            </button>
          </div>
        </div>
      </section>
    </template>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-text">{{ successMessage }}</p>
  </article>
</template>

<style scoped>
.cloud-account-panel {
  display: grid;
  align-content: start;
  gap: var(--zs-space-4);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

h2 {
  margin: 0;
  font-size: 1.25rem;
  line-height: 1.2;
}

h3 {
  margin: 0 0 var(--zs-space-2);
  font-size: 0.95rem;
}

.panel-copy {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.loading-state {
  padding: var(--zs-space-3) 0;
  color: var(--zs-color-text-muted);
}

section {
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-3);
}

.profile-row,
.action-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  flex-wrap: wrap;
}

.profile-label,
.action-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  min-width: 80px;
}

.profile-value {
  color: var(--zs-color-text);
  font-weight: 800;
}

.text-input {
  min-height: 32px;
  padding: 4px 10px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  font: inherit;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

button {
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.small-button {
  min-height: 30px;
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-size: 0.85rem;
  padding: 0 10px;
}

.small-button.ghost {
  background: transparent;
}

.danger-button {
  background: var(--zs-color-danger);
  color: #fff;
}

.password-form,
.delete-form {
  margin-top: var(--zs-space-3);
  display: grid;
  gap: var(--zs-space-3);
}

.form-field {
  display: grid;
  gap: 4px;
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
}

.form-field .text-input {
  width: 100%;
  max-width: 300px;
}

.form-actions {
  display: flex;
  gap: var(--zs-space-2);
}

.danger-section {
  border-color: var(--zs-color-danger);
}

.warning-text {
  margin: 0;
  color: var(--zs-color-danger);
  font-weight: 800;
}

.deletion-confirm ul {
  margin: 0;
  padding-left: 20px;
  color: var(--zs-color-text);
}

.deletion-confirm code {
  background: var(--zs-color-surface-soft);
  padding: 2px 6px;
  border-radius: var(--zs-radius-sm);
  font-weight: 800;
}

.error-text {
  margin: 0;
  color: var(--zs-color-danger);
  font-weight: 800;
}

.success-text {
  margin: 0;
  color: var(--zs-color-success);
  font-weight: 800;
}
</style>

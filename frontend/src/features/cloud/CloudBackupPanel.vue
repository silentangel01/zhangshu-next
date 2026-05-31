<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  enableCloud,
  getCloudAccountStatus,
  getCloudStatus,
  listCloudBackups,
  listRemoteCloudProjects,
  restoreCloudBackup,
  runCloudSync,
  triggerCloudBackup,
} from '@/entities/cloud/api'
import type {
  CloudAccountStatus,
  CloudBackupRecord,
  CloudProjectStatus,
  CloudRemoteProject,
} from '@/entities/cloud/types'
import { ApiError } from '@/shared/api/client'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const props = defineProps<{
  projectId: string
}>()

const isLoading = ref(true)
const isEnabling = ref(false)
const isBackingUp = ref(false)
const isSyncing = ref(false)
const isRestoring = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const syncMessage = ref('')

const accountStatus = ref<CloudAccountStatus | null>(null)
const cloudStatus = ref<CloudProjectStatus | null>(null)
const backups = ref<CloudBackupRecord[]>([])

const isLoggedIn = ref(false)
const cloudEnabled = ref(false)

// ── Link existing cloud project state ──────────────────────────
const showLinkDialog = ref(false)
const isLinkDialogLoading = ref(false)
const isLinking = ref(false)
const isInitialSyncing = ref(false)
const remoteProjects = ref<CloudRemoteProject[]>([])
const linkErrorMessage = ref('')
const linkSuggestionMessage = ref('')

onMounted(async () => {
  try {
    const [acctStatus, projStatus] = await Promise.all([
      getCloudAccountStatus(),
      getCloudStatus(props.projectId).catch(() => null),
    ])
    accountStatus.value = acctStatus
    isLoggedIn.value = acctStatus.logged_in

    if (projStatus && projStatus.cloud_enabled) {
      cloudStatus.value = projStatus
      cloudEnabled.value = true
      const backupList = await listCloudBackups(props.projectId)
      backups.value = backupList.items
    }
  } catch {
    errorMessage.value = '加载云端备份状态失败。'
  } finally {
    isLoading.value = false
  }
})

async function handleEnableCloud() {
  isEnabling.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const status = await enableCloud(props.projectId)
    cloudStatus.value = status
    cloudEnabled.value = true
    successMessage.value = '已启用云端保存。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '启用云端保存失败。')
  } finally {
    isEnabling.value = false
  }
}

// ── Link existing cloud project handlers ──────────────────────

async function handleOpenLinkDialog() {
  showLinkDialog.value = true
  isLinkDialogLoading.value = true
  linkErrorMessage.value = ''
  linkSuggestionMessage.value = ''
  remoteProjects.value = []

  try {
    remoteProjects.value = await listRemoteCloudProjects()
  } catch (error) {
    linkErrorMessage.value =
      error instanceof Error ? error.message : '加载云端项目列表失败。'
    if (error instanceof ApiError && error.suggestion) {
      linkSuggestionMessage.value = error.suggestion
    }
  } finally {
    isLinkDialogLoading.value = false
  }
}

function handleCloseLinkDialog() {
  showLinkDialog.value = false
  linkErrorMessage.value = ''
  linkSuggestionMessage.value = ''
  remoteProjects.value = []
}

async function handleSelectCloudProject(project: CloudRemoteProject) {
  isLinking.value = true
  linkErrorMessage.value = ''
  linkSuggestionMessage.value = ''

  try {
    const status = await enableCloud(props.projectId, project.id)
    cloudStatus.value = status
    cloudEnabled.value = true
    showLinkDialog.value = false
    remoteProjects.value = []
  } catch (error) {
    linkErrorMessage.value =
      error instanceof Error ? error.message : '关联云端项目失败。'
    if (error instanceof ApiError && error.suggestion) {
      linkSuggestionMessage.value = error.suggestion
    }
    isLinking.value = false
    return
  }

  isLinking.value = false

  // Run initial bidirectional sync: push local dirty records + pull remote changes
  isInitialSyncing.value = true
  successMessage.value = '正在同步云端数据…'
  try {
    const syncResult = await runCloudSync(props.projectId)
    const pushed = syncResult.pushed ?? 0
    const pulled = syncResult.pulled ?? 0

    if (pushed > 0 && pulled > 0) {
      successMessage.value = `已关联并同步完成，上传 ${pushed} 条、拉取 ${pulled} 条更新。`
    } else if (pushed > 0) {
      successMessage.value = `已关联并上传本机数据。`
    } else if (pulled > 0) {
      successMessage.value = `已关联并拉取云端更新。`
    } else {
      successMessage.value = '已关联云端项目，本机数据已是最新。'
    }

    // Refresh cloud status and backups after sync
    try {
      const projStatus = await getCloudStatus(props.projectId)
      cloudStatus.value = projStatus
      const backupList = await listCloudBackups(props.projectId)
      backups.value = backupList.items
    } catch {
      // ignore refresh failure
    }
  } catch (error) {
    // Linking succeeded but sync failed — show partial success
    successMessage.value = '已关联云端项目。'
    errorMessage.value = '首次同步失败，本机内容已保留，可稍后点击"立即同步"重试。'
  } finally {
    isInitialSyncing.value = false
  }
}

async function handleSyncNow() {
  isSyncing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  syncMessage.value = ''

  try {
    const result = await runCloudSync(props.projectId)
    const { syncMsg, errorMsg } = formatManualSyncResult(result)
    syncMessage.value = syncMsg
    errorMessage.value = errorMsg
  } catch {
    errorMessage.value = '同步失败，本机内容已保留，可稍后重试。'
  } finally {
    isSyncing.value = false
  }
}

async function handleTriggerBackup() {
  isBackingUp.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const record = await triggerCloudBackup(props.projectId)
    backups.value = [record, ...backups.value.filter((b) => b.id !== record.id)]
    successMessage.value = '云端备份成功。'

    const projStatus = await getCloudStatus(props.projectId)
    cloudStatus.value = projStatus
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '云端备份失败。')
    try {
      const backupList = await listCloudBackups(props.projectId)
      backups.value = backupList.items
    } catch {
      // ignore refresh failure
    }
  } finally {
    isBackingUp.value = false
  }
}

async function handleRestore(recordId: string) {
  isRestoring.value = recordId
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const report = await restoreCloudBackup(props.projectId, recordId)
    successMessage.value = `已恢复为新项目：${report.project_title}`
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '恢复云端备份失败。')
  } finally {
    isRestoring.value = ''
  }
}

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STATUS_LABELS: Record<string, string> = {
  pending: '上传中',
  success: '已完成',
  failed: '失败',
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    const msg = error.message
    // Detect common OSS-specific issues
    if (msg.includes('403')) {
      return '上传失败 (403)：可能是签名过期、OSS 地址配置错误或权限不足。请在应用设置中运行连接诊断。'
    }
    if (msg.includes('-internal.aliyuncs.com')) {
      return '上传失败：OSS 地址配置为内网地址，桌面端无法访问。请联系管理员修正。'
    }
    if (msg.includes('签名') || msg.includes('SignatureDoesNotMatch')) {
      return '上传失败：签名不匹配，请重试或检查时间是否同步。'
    }
    return msg
  }
  return fallback
}

function formatManualSyncResult(result: {
  pushed: number
  pulled: number
  conflicts: number
  errors: string[]
}): { syncMsg: string; errorMsg: string } {
  const pushed = result.pushed ?? 0
  const pulled = result.pulled ?? 0

  // Partial failure: errors exist
  if (result.errors.length > 0) {
    const summary =
      pushed > 0 || pulled > 0
        ? `已上传 ${pushed} 条、拉取 ${pulled} 条，但部分同步未完成。`
        : '同步未完全完成。'
    return {
      syncMsg: summary,
      errorMsg: '本机内容已保留，可稍后重试。',
    }
  }

  // Conflicts
  if (result.conflicts > 0) {
    return {
      syncMsg:
        pushed > 0 || pulled > 0
          ? `上传 ${pushed} 条、拉取 ${pulled} 条。部分内容存在多设备修改，请在备份面板中检查。`
          : '部分内容存在多设备修改，请在备份面板中检查。',
      errorMsg: '',
    }
  }

  // Full success
  if (pushed > 0 && pulled > 0) {
    return { syncMsg: `同步完成，上传 ${pushed} 条、拉取 ${pulled} 条更新。`, errorMsg: '' }
  }
  if (pushed > 0) {
    return { syncMsg: `同步完成，上传 ${pushed} 条。`, errorMsg: '' }
  }
  if (pulled > 0) {
    return { syncMsg: `同步完成，拉取 ${pulled} 条更新。`, errorMsg: '' }
  }
  return { syncMsg: '数据已是最新。', errorMsg: '' }
}
</script>

<template>
  <article class="action-panel cloud-backup-panel">
    <header>
      <p class="eyebrow">云端备份</p>
      <h2>云端同步与备份</h2>
    </header>
    <p class="panel-copy">
      日常更改会通过增量同步自动保存到云端；完整备份用于手动留档和恢复。本机数据始终保留。
    </p>

    <div v-if="isLoading" class="loading-state">正在加载…</div>

    <template v-else>
      <!-- Not logged in -->
      <div v-if="!isLoggedIn" class="prompt-section">
        <p class="prompt-text">登录章枢云账户后可启用云端保存。</p>
      </div>

      <!-- Logged in but not enabled -->
      <div v-else-if="!cloudEnabled" class="prompt-section">
        <button
          class="primary-button"
          type="button"
          :disabled="isEnabling"
          @click="handleEnableCloud"
        >
          {{ isEnabling ? '正在启用…' : '为本书启用云端保存' }}
        </button>
        <button
          class="secondary-button"
          type="button"
          @click="handleOpenLinkDialog"
        >
          关联已有云端项目
        </button>
      </div>

      <!-- Enabled -->
      <div v-else class="enabled-section">
        <div class="backup-actions">
          <button
            class="primary-button"
            type="button"
            :disabled="isSyncing"
            @click="handleSyncNow"
          >
            {{ isSyncing ? '正在同步…' : '立即同步' }}
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="isBackingUp"
            @click="handleTriggerBackup"
          >
            {{ isBackingUp ? '正在上传…' : '创建完整备份' }}
          </button>
          <p v-if="cloudStatus?.last_backup_at" class="last-backup">
            上次备份：{{ formatDateTime(cloudStatus.last_backup_at) }}
          </p>
        </div>

        <p v-if="syncMessage" class="sync-message">{{ syncMessage }}</p>

        <div v-if="backups.length > 0" class="backup-list">
          <h3>完整备份记录</h3>
          <ul>
            <li v-for="record in backups" :key="record.id" class="backup-row">
              <div class="backup-info">
                <span class="backup-filename">{{ record.filename }}</span>
                <span class="backup-meta">
                  {{ formatBytes(record.size_bytes) }} ·
                  {{ formatDateTime(record.uploaded_at ?? record.created_at) }} ·
                  {{ STATUS_LABELS[record.status] ?? record.status }}
                </span>
              </div>
              <button
                v-if="record.status === 'success'"
                class="small-button"
                type="button"
                :disabled="isRestoring === record.id"
                @click="handleRestore(record.id)"
              >
                {{ isRestoring === record.id ? '恢复中…' : '恢复为新项目' }}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </template>

    <div v-if="isInitialSyncing" class="syncing-banner">
      <span class="syncing-spinner" />
      <span>正在从云端拉取最新数据…</span>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-text">{{ successMessage }}</p>

    <!-- Link existing cloud project dialog -->
    <div v-if="showLinkDialog" class="dialog-overlay" @click.self="handleCloseLinkDialog">
      <div class="dialog-panel">
        <header class="dialog-header">
          <h2>关联已有云端项目</h2>
          <button class="close-button" type="button" @click="handleCloseLinkDialog">×</button>
        </header>

        <section v-if="linkErrorMessage" class="error-banner" role="alert">
          <p class="error-banner-text">{{ linkErrorMessage }}</p>
          <p v-if="linkSuggestionMessage" class="suggestion-text">{{ linkSuggestionMessage }}</p>
        </section>

        <section class="dialog-body">
          <div v-if="isLinkDialogLoading" class="state-message">正在加载云端项目…</div>

          <div v-else-if="remoteProjects.length === 0" class="state-message">
            云端没有可关联的项目。
          </div>

          <ul v-else class="project-list">
            <li v-for="project in remoteProjects" :key="project.id" class="project-item">
              <div class="project-info">
                <strong>{{ project.title }}</strong>
                <span v-if="project.updated_at" class="project-date">
                  更新于 {{ project.updated_at.slice(0, 10) }}
                </span>
                <span v-if="project.linked_locally" class="project-linked-badge">
                  本机已有
                </span>
              </div>
              <button
                v-if="project.linked_locally"
                class="small-button"
                type="button"
                disabled
              >
                已关联
              </button>
              <button
                v-else
                class="primary-button small-primary-button"
                type="button"
                :disabled="isLinking"
                @click="handleSelectCloudProject(project)"
              >
                {{ isLinking ? '关联中…' : '关联此项目' }}
              </button>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </article>
</template>

<style scoped>
.cloud-backup-panel {
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

.prompt-section {
  display: grid;
  gap: var(--zs-space-3);
}

.prompt-text {
  margin: 0;
  color: var(--zs-color-text-muted);
}

.enabled-section {
  display: grid;
  gap: var(--zs-space-4);
}

.backup-actions {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
}

.last-backup {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.backup-list {
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-3);
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-2);
}

.backup-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: 10px 12px;
  background: var(--zs-color-surface-soft);
}

.backup-info {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.backup-filename {
  color: var(--zs-color-text);
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.backup-meta {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
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

.primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border: 1px solid var(--zs-color-border);
  font-weight: 600;
}

.secondary-button:hover {
  background: var(--zs-color-surface-soft, #f5f5f5);
}

.small-primary-button {
  min-height: 30px;
  font-size: 0.85rem;
  padding: 0 10px;
}

/* ── Link dialog styles ────────────────────────────────────────── */

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.4);
}

.dialog-panel {
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.18));
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--zs-color-border);
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--zs-color-text-muted);
  padding: 0 4px;
  line-height: 1;
}

.dialog-body {
  overflow-y: auto;
  padding: 16px 20px;
}

.error-banner {
  margin: 0 20px;
  padding: 10px 14px;
  border: 1px solid var(--zs-color-danger);
  border-radius: 8px;
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-size: 0.86rem;
}

.error-banner-text {
  margin: 0;
  font-weight: 700;
}

.suggestion-text {
  margin: 6px 0 0;
  color: var(--zs-color-text-muted);
  font-weight: 400;
  font-size: 0.82rem;
  line-height: 1.5;
}

.state-message {
  text-align: center;
  color: var(--zs-color-text-muted);
  padding: 40px 0;
}

.project-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface-soft, #fafafa);
}

.project-info {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.project-info strong {
  font-size: 0.92rem;
}

.project-date {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.project-linked-badge {
  display: inline-block;
  margin-top: 2px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #16a34a);
  font-size: 0.72rem;
  font-weight: 600;
  width: fit-content;
}

.small-button {
  min-height: 30px;
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-size: 0.85rem;
  padding: 0 10px;
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

.sync-message {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.88rem;
}

.syncing-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-primary-soft, #eff6ff);
  color: var(--zs-color-primary);
  font-size: 0.88rem;
  font-weight: 600;
}

.syncing-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--zs-color-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

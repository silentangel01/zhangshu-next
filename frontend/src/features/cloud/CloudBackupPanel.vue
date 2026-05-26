<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  enableCloud,
  getCloudAccountStatus,
  getCloudStatus,
  listCloudBackups,
  restoreCloudBackup,
  triggerCloudBackup,
} from '@/entities/cloud/api'
import type {
  CloudAccountStatus,
  CloudBackupRecord,
  CloudProjectStatus,
  CloudRestoreReport,
} from '@/entities/cloud/types'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const props = defineProps<{
  projectId: string
}>()

const isLoading = ref(true)
const isEnabling = ref(false)
const isBackingUp = ref(false)
const isRestoring = ref('')
const errorMessage = ref('')
const successMessage = ref('')

const accountStatus = ref<CloudAccountStatus | null>(null)
const cloudStatus = ref<CloudProjectStatus | null>(null)
const backups = ref<CloudBackupRecord[]>([])

const isLoggedIn = ref(false)
const cloudEnabled = ref(false)

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
</script>

<template>
  <article class="action-panel cloud-backup-panel">
    <header>
      <p class="eyebrow">云端备份</p>
      <h2>章枢云端保存</h2>
    </header>
    <p class="panel-copy">
      将项目备份上传到章枢云，支持多端恢复。本地数据始终保留。
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
      </div>

      <!-- Enabled -->
      <div v-else class="enabled-section">
        <div class="backup-actions">
          <button
            class="primary-button"
            type="button"
            :disabled="isBackingUp"
            @click="handleTriggerBackup"
          >
            {{ isBackingUp ? '正在上传…' : '立即云端保存' }}
          </button>
          <p v-if="cloudStatus?.last_backup_at" class="last-backup">
            上次备份：{{ formatDateTime(cloudStatus.last_backup_at) }}
          </p>
        </div>

        <div v-if="backups.length > 0" class="backup-list">
          <h3>备份记录</h3>
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

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-text">{{ successMessage }}</p>
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
</style>

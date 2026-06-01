<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getCloudUsage } from '@/entities/cloud/api'
import type { CloudUsage } from '@/entities/cloud/types'

const isLoading = ref(true)
const errorMessage = ref('')
const usage = ref<CloudUsage | null>(null)

onMounted(async () => {
  try {
    usage.value = await getCloudUsage()
  } catch {
    errorMessage.value = '加载使用量失败。'
  } finally {
    isLoading.value = false
  }
})

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function getPercentage(used: number, quota: number): number {
  if (quota <= 0) return 0
  return Math.min(100, Math.round((used / quota) * 100))
}
</script>

<template>
  <article class="action-panel cloud-usage-panel">
    <header>
      <p class="eyebrow">使用量</p>
      <h2>云存储与配额</h2>
    </header>
    <p class="panel-copy">
      查看你的章枢云使用量和配额限制。
    </p>

    <div v-if="isLoading" class="loading-state">正在加载…</div>

    <template v-else-if="usage">
      <section class="usage-section">
        <div class="usage-row">
          <div class="usage-info">
            <span class="usage-label">存储空间</span>
            <span class="usage-value">
              {{ formatBytes(usage.storage_used_bytes) }} / {{ formatBytes(usage.storage_quota_bytes) }}
            </span>
          </div>
          <div class="usage-bar">
            <div
              class="usage-bar-fill"
              :class="{ warning: getPercentage(usage.storage_used_bytes, usage.storage_quota_bytes) > 80 }"
              :style="{ width: getPercentage(usage.storage_used_bytes, usage.storage_quota_bytes) + '%' }"
            ></div>
          </div>
        </div>

        <div class="usage-row">
          <div class="usage-info">
            <span class="usage-label">备份数量</span>
            <span class="usage-value">
              {{ usage.backup_count }} / {{ usage.backup_count_quota }}
            </span>
          </div>
          <div class="usage-bar">
            <div
              class="usage-bar-fill"
              :class="{ warning: getPercentage(usage.backup_count, usage.backup_count_quota) > 80 }"
              :style="{ width: getPercentage(usage.backup_count, usage.backup_count_quota) + '%' }"
            ></div>
          </div>
        </div>

        <div class="usage-row">
          <div class="usage-info">
            <span class="usage-label">每小时备份次数</span>
            <span class="usage-value">
              {{ usage.backup_init_used_last_hour }} / {{ usage.backup_init_limit_per_hour }}
            </span>
          </div>
          <div class="usage-bar">
            <div
              class="usage-bar-fill"
              :class="{ warning: getPercentage(usage.backup_init_used_last_hour, usage.backup_init_limit_per_hour) > 80 }"
              :style="{ width: getPercentage(usage.backup_init_used_last_hour, usage.backup_init_limit_per_hour) + '%' }"
            ></div>
          </div>
        </div>

        <div class="usage-row">
          <div class="usage-info">
            <span class="usage-label">单文件大小上限</span>
            <span class="usage-value">{{ formatBytes(usage.max_backup_size_bytes) }}</span>
          </div>
        </div>
      </section>
    </template>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
  </article>
</template>

<style scoped>
.cloud-usage-panel {
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

.panel-copy {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.loading-state {
  padding: var(--zs-space-3) 0;
  color: var(--zs-color-text-muted);
}

.usage-section {
  display: grid;
  gap: var(--zs-space-4);
}

.usage-row {
  display: grid;
  gap: var(--zs-space-2);
}

.usage-info {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.usage-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.usage-value {
  color: var(--zs-color-text);
  font-weight: 800;
  font-size: 0.9rem;
}

.usage-bar {
  height: 8px;
  background: var(--zs-color-surface-soft);
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
}

.usage-bar-fill {
  height: 100%;
  background: var(--zs-color-primary);
  transition: width 0.3s ease;
}

.usage-bar-fill.warning {
  background: var(--zs-color-warning, #e67e22);
}

.error-text {
  margin: 0;
  color: var(--zs-color-danger);
  font-weight: 800;
}
</style>

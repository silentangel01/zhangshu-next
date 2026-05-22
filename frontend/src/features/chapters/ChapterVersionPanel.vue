<script setup lang="ts">
import type { ChapterVersionListItem, ChapterVersionSource } from '@/entities/chapter-version/types'

defineProps<{
  versions: ChapterVersionListItem[]
  isLoading: boolean
  errorMessage: string
  isBusy: boolean
}>()

const emit = defineEmits<{
  createSnapshot: []
  viewVersion: [versionId: string]
  restoreVersion: [versionId: string]
}>()

function getSourceLabel(source: ChapterVersionSource): string {
  const labels: Record<ChapterVersionSource, string> = {
    manual: '手动保存',
    autosave: '自动保存',
    restore: '恢复版本',
    before_restore: '恢复前备份',
  }

  return labels[source]
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
</script>

<template>
  <section class="version-panel" aria-label="版本历史">
    <header class="version-panel-header">
      <div>
        <p class="eyebrow">历史</p>
        <h3>版本</h3>
      </div>
      <button class="primary-button" type="button" :disabled="isBusy" @click="emit('createSnapshot')">
        创建版本快照
      </button>
    </header>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="state-message">正在加载版本历史……</p>
    <p v-else-if="!versions.length" class="state-message">暂无版本历史</p>

    <ul v-else class="version-list">
      <li v-for="version in versions" :key="version.id" class="version-item">
        <div class="version-main">
          <strong>{{ getSourceLabel(version.source) }}</strong>
          <span>字数：{{ version.word_count }}</span>
          <span>创建时间：{{ formatDateTime(version.created_at) }}</span>
          <p v-if="version.note">{{ version.note }}</p>
        </div>
        <div class="version-actions">
          <button type="button" @click="emit('viewVersion', version.id)">查看</button>
          <button type="button" :disabled="isBusy" @click="emit('restoreVersion', version.id)">
            恢复
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.version-panel {
  display: grid;
  gap: 12px;
  margin-top: 22px;
  border-top: 1px solid #edf0f5;
  padding-top: 18px;
}

.version-panel-header,
.version-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

h3 {
  margin: 0;
  color: #111827;
  font-size: 1.05rem;
}

.state-message,
.error-message {
  margin: 0;
  color: #64748b;
  font-weight: 700;
}

.error-message {
  color: #b42318;
}

.version-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.version-item {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}

.version-main {
  display: grid;
  gap: 4px;
  color: #64748b;
  font-size: 0.88rem;
}

.version-main strong {
  color: #111827;
  font-size: 0.95rem;
}

.version-main p {
  margin: 2px 0 0;
}

.version-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

button {
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 12px;
  background: #ffffff;
  color: #374151;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-button {
  min-height: 38px;
  border-color: transparent;
  background: #2563eb;
  color: #ffffff;
}

@media (max-width: 720px) {
  .version-panel-header,
  .version-item {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button {
    width: 100%;
  }
}
</style>

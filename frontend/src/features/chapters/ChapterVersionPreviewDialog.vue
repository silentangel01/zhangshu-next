<script setup lang="ts">
import type { ChapterVersionDetail } from '@/entities/chapter-version/types'
import { CHAPTER_VERSION_SOURCE_LABELS } from '@/entities/chapter-version/types'
import { formatDateTimeFull } from '@/shared/utils/formatDateTime'

defineProps<{
  version: ChapterVersionDetail
}>()

const emit = defineEmits<{
  close: []
  restore: [versionId: string]
}>()

function getSourceLabel(source: string): string {
  return CHAPTER_VERSION_SOURCE_LABELS[source] ?? source
}
</script>

<template>
  <div class="dialog-backdrop" role="presentation">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="version-preview-title">
      <header class="dialog-header">
        <div>
          <p class="eyebrow">版本预览</p>
          <h2 id="version-preview-title">{{ version.title }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">x</button>
      </header>

      <dl class="metadata-grid">
        <div>
          <dt>版本来源</dt>
          <dd>{{ getSourceLabel(version.source) }}</dd>
        </div>
        <div>
          <dt>字数</dt>
          <dd>{{ version.word_count }}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{{ formatDateTimeFull(version.created_at) }}</dd>
        </div>
      </dl>

      <p v-if="version.note" class="note">{{ version.note }}</p>

      <pre class="content-preview">{{ version.content || '暂无正文内容' }}</pre>

      <footer class="dialog-actions">
        <button class="secondary-button" type="button" @click="emit('close')">关闭</button>
        <button class="primary-button" type="button" @click="emit('restore', version.id)">
          恢复
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(20 24 31 / 54%);
}

.dialog {
  display: grid;
  gap: 18px;
  width: min(760px, 100%);
  max-height: min(820px, calc(100vh - 48px));
  box-sizing: border-box;
  overflow: auto;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 24px;
  background: var(--zs-color-surface);
  box-shadow: 0 24px 80px rgb(20 24 31 / 22%);
}

.dialog-header,
.dialog-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.25rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 0;
}

.metadata-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-bg);
}

dt {
  margin: 0 0 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

dd,
.note {
  margin: 0;
  color: var(--zs-color-text);
  font-weight: 700;
}

.content-preview {
  min-height: 280px;
  margin: 0;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
  font: inherit;
  line-height: 1.8;
  white-space: pre-wrap;
}

button {
  min-height: 38px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.icon-button {
  width: 36px;
  min-height: 36px;
  padding: 0;
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}
</style>

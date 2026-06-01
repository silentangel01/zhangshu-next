<script setup lang="ts">
import type { Announcement } from '@/entities/announcement/types'

const props = defineProps<{
  announcement: Announcement
}>()

const emit = defineEmits<{
  close: []
  dismiss: []
}>()

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function handleDismiss() {
  emit('dismiss')
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="dialog-overlay" @click.self="emit('close')">
      <div class="dialog-panel announcement-detail-dialog">
        <header class="dialog-header">
          <h2 class="dialog-title">{{ props.announcement.title }}</h2>
          <button class="dialog-close-btn" type="button" @click="emit('close')">✕</button>
        </header>

        <div class="dialog-body">
          <p v-if="props.announcement.published_at" class="meta-date">
            发布于 {{ formatDate(props.announcement.published_at) }}
          </p>
          <div class="announcement-body">
            <p v-for="(line, idx) in props.announcement.body.split('\n')" :key="idx">
              {{ line }}
            </p>
          </div>
        </div>

        <footer class="dialog-footer">
          <button class="btn-secondary" type="button" @click="emit('close')">关闭</button>
          <button class="btn-danger-outline" type="button" @click="handleDismiss">
            不再显示
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
}

.announcement-detail-dialog {
  width: 90%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--zs-color-surface, #fff);
  border-radius: var(--zs-radius-lg, 8px);
  box-shadow: var(--zs-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.15));
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--zs-space-4, 16px);
  border-bottom: 1px solid var(--zs-color-border, #ddd);
}

.dialog-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.dialog-close-btn {
  border: none;
  background: transparent;
  font-size: 1.25rem;
  cursor: pointer;
  opacity: 0.5;
  color: inherit;
}

.dialog-close-btn:hover {
  opacity: 1;
}

.dialog-body {
  padding: var(--zs-space-4, 16px);
  overflow-y: auto;
  flex: 1;
}

.meta-date {
  font-size: 0.8125rem;
  opacity: 0.6;
  margin-bottom: var(--zs-space-3, 12px);
}

.announcement-body p {
  margin: 0 0 0.5em;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--zs-space-2, 8px);
  padding: var(--zs-space-3, 12px) var(--zs-space-4, 16px);
  border-top: 1px solid var(--zs-color-border, #ddd);
}

.btn-secondary {
  padding: 6px 16px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: transparent;
  cursor: pointer;
  color: inherit;
  font-size: 0.875rem;
}

.btn-secondary:hover {
  background: var(--zs-color-surface-hover, #f5f5f5);
}

.btn-danger-outline {
  padding: 6px 16px;
  border: 1px solid var(--zs-color-danger, #ef4444);
  border-radius: var(--zs-radius-sm, 4px);
  background: transparent;
  cursor: pointer;
  color: var(--zs-color-danger, #ef4444);
  font-size: 0.875rem;
}

.btn-danger-outline:hover {
  background: var(--zs-color-danger-bg, #fef2f2);
}
</style>

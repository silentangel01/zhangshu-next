<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { listAnnouncements } from '@/entities/announcement/api'
import type { Announcement } from '@/entities/announcement/types'

import AnnouncementDetailDialog from './AnnouncementDetailDialog.vue'

const DISMISSED_KEY = 'zhangshu:dismissed-announcements'

const currentAnnouncement = ref<Announcement | null>(null)
const showDetail = ref(false)
const isLoading = ref(true)

onMounted(async () => {
  try {
    const res = await listAnnouncements()
    if (res.items.length > 0) {
      const dismissed = getDismissedIds()
      const visible = res.items.filter((a) => !dismissed.has(a.id))
      if (visible.length > 0) {
        // Show highest severity first
        currentAnnouncement.value = visible.sort(bySeverity)[0]!
      }
    }
  } catch {
    // Cloud unavailable — silently hide
  } finally {
    isLoading.value = false
  }
})

function dismiss() {
  if (currentAnnouncement.value) {
    addDismissedId(currentAnnouncement.value.id)
    currentAnnouncement.value = null
  }
}

function openDetail() {
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
}

// Severity ordering: critical > warning > success > info
const SEVERITY_ORDER: Record<string, number> = {
  critical: 4,
  warning: 3,
  success: 2,
  info: 1,
}

function bySeverity(a: Announcement, b: Announcement): number {
  return (SEVERITY_ORDER[b.severity] ?? 0) - (SEVERITY_ORDER[a.severity] ?? 0)
}

function getDismissedIds(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY)
    if (raw) return new Set(JSON.parse(raw) as string[])
  } catch {
    /* ignore */
  }
  return new Set()
}

function addDismissedId(id: string) {
  const ids = getDismissedIds()
  ids.add(id)
  localStorage.setItem(DISMISSED_KEY, JSON.stringify([...ids]))
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = {
    info: '通知',
    success: '好消息',
    warning: '注意',
    critical: '重要',
  }
  return map[severity] ?? severity
}
</script>

<template>
  <Transition name="banner-slide">
    <div
      v-if="currentAnnouncement && !isLoading"
      :class="['announcement-banner', `severity-${currentAnnouncement.severity}`]"
    >
      <span class="banner-severity">{{ severityLabel(currentAnnouncement.severity) }}</span>
      <span class="banner-title">{{ currentAnnouncement.title }}</span>
      <button class="banner-detail-btn" type="button" @click="openDetail">
        查看详情
      </button>
      <button class="banner-dismiss-btn" type="button" title="关闭" @click="dismiss">
        ✕
      </button>
    </div>
  </Transition>

  <AnnouncementDetailDialog
    v-if="showDetail && currentAnnouncement"
    :announcement="currentAnnouncement"
    @close="closeDetail"
    @dismiss="dismiss"
  />
</template>

<style scoped>
.announcement-banner {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2, 8px);
  padding: var(--zs-space-2, 8px) var(--zs-space-4, 16px);
  font-size: 0.875rem;
  border-bottom: 1px solid var(--zs-color-border, #ddd);
  background: var(--zs-color-surface, #fff);
  min-height: 40px;
}

.severity-info {
  border-left: 3px solid var(--zs-color-info, #3b82f6);
}
.severity-success {
  border-left: 3px solid var(--zs-color-success, #22c55e);
}
.severity-warning {
  border-left: 3px solid var(--zs-color-warning, #f59e0b);
  background: var(--zs-color-warning-bg, #fffbeb);
}
.severity-critical {
  border-left: 3px solid var(--zs-color-danger, #ef4444);
  background: var(--zs-color-danger-bg, #fef2f2);
}

.banner-severity {
  font-weight: 600;
  flex-shrink: 0;
}

.banner-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.banner-detail-btn {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 0.8125rem;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: transparent;
  cursor: pointer;
  color: inherit;
}

.banner-detail-btn:hover {
  background: var(--zs-color-surface-hover, #f5f5f5);
}

.banner-dismiss-btn {
  flex-shrink: 0;
  padding: 2px 6px;
  font-size: 0.875rem;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0.5;
  color: inherit;
}

.banner-dismiss-btn:hover {
  opacity: 1;
}

.banner-slide-enter-active,
.banner-slide-leave-active {
  transition: all 0.3s ease;
}
.banner-slide-enter-from,
.banner-slide-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}
</style>

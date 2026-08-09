<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { listAnnouncements } from '@/entities/announcement/api'
import type { Announcement } from '@/entities/announcement/types'

import AnnouncementDetailDialog from './AnnouncementDetailDialog.vue'

const READ_KEY = 'zhangshu:read-announcements'

const announcements = ref<Announcement[]>([])
const isPanelOpen = ref(false)
const selectedAnnouncement = ref<Announcement | null>(null)
const isLoading = ref(false)

const bellRef = ref<HTMLButtonElement | null>(null)
const panelRef = ref<HTMLDivElement | null>(null)

onMounted(async () => {
  await fetchAnnouncements()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function fetchAnnouncements() {
  isLoading.value = true
  try {
    const res = await listAnnouncements()
    announcements.value = res.items
  } catch {
    announcements.value = []
  } finally {
    isLoading.value = false
  }
}

function getReadIds(): Set<string> {
  try {
    const raw = localStorage.getItem(READ_KEY)
    if (raw) return new Set(JSON.parse(raw) as string[])
  } catch {
    /* ignore */
  }
  return new Set()
}

function markAsRead(id: string) {
  const ids = getReadIds()
  ids.add(id)
  localStorage.setItem(READ_KEY, JSON.stringify([...ids]))
}

function isRead(id: string): boolean {
  return getReadIds().has(id)
}

const unreadCount = computed(() => {
  const readIds = getReadIds()
  return announcements.value.filter((a) => !readIds.has(a.id)).length
})

function togglePanel() {
  isPanelOpen.value = !isPanelOpen.value
  if (isPanelOpen.value) {
    fetchAnnouncements()
  }
}

function handleClickOutside(event: MouseEvent) {
  if (!isPanelOpen.value) return

  const target = event.target as Node
  if (bellRef.value?.contains(target) || panelRef.value?.contains(target)) {
    return
  }
  isPanelOpen.value = false
}

function openDetail(announcement: Announcement) {
  selectedAnnouncement.value = announcement
  markAsRead(announcement.id)
}

function closeDetail() {
  selectedAnnouncement.value = null
  fetchAnnouncements()
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))

    if (hours < 1) return '刚刚'
    if (hours < 24) return `${hours} 小时前`
    if (hours < 48) return '昨天'
    if (hours < 168) return `${Math.floor(hours / 24)} 天前`

    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  } catch {
    return dateStr
  }
}

function severityIcon(): string {
  return '●'
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    critical: '紧急',
    warning: '警告',
    success: '好消息',
    info: '通知',
  }
  return labels[severity] ?? severity
}
</script>

<template>
  <div class="notification-wrapper">
    <button
      ref="bellRef"
      type="button"
      class="notification-bell"
      :class="{ active: isPanelOpen }"
      title="通知中心"
      @click="togglePanel"
    >
      <svg class="bell-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6.8 9.5a5.2 5.2 0 0 1 10.4 0c0 5 2 5.8 2 5.8H4.8s2-.8 2-5.8Z" />
        <path d="M9.8 18.2a2.4 2.4 0 0 0 4.4 0" />
      </svg>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <Transition name="panel-slide">
      <div v-if="isPanelOpen" ref="panelRef" class="notification-panel">
        <header class="panel-header">
          <h3 class="panel-title">通知中心</h3>
          <span v-if="unreadCount > 0" class="panel-unread">{{ unreadCount }} 条未读</span>
        </header>

        <div v-if="isLoading" class="panel-loading">加载中...</div>

        <div v-else-if="announcements.length === 0" class="panel-empty">
          <p class="empty-icon">—</p>
          <p>暂无通知</p>
        </div>

        <ul v-else class="announcement-list">
          <li
            v-for="ann in announcements"
            :key="ann.id"
            class="announcement-item"
            :class="{ unread: !isRead(ann.id) }"
            @click="openDetail(ann)"
          >
            <div class="item-header">
              <span class="severity-dot" :class="`severity-${ann.severity}`">{{
                severityIcon()
              }}</span>
              <span class="item-title">{{ ann.title }}</span>
            </div>
            <div class="item-meta">
              <span class="severity-label">{{ severityLabel(ann.severity) }}</span>
              <span class="item-date">{{ formatDate(ann.published_at) }}</span>
            </div>
          </li>
        </ul>
      </div>
    </Transition>
  </div>

  <AnnouncementDetailDialog
    v-if="selectedAnnouncement"
    :announcement="selectedAnnouncement"
    @close="closeDetail"
    @dismiss="closeDetail"
  />
</template>

<style scoped>
.notification-wrapper {
  position: relative;
}

.notification-bell {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  cursor: pointer;
  transition:
    background var(--zs-duration-fast) var(--zs-ease-standard),
    border-color var(--zs-duration-fast) var(--zs-ease-standard);
}

.notification-bell:hover {
  background: var(--zs-color-surface-soft);
  border-color: var(--zs-color-border-strong);
}

.notification-bell.active {
  background: var(--zs-color-surface-soft);
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-focus);
}

.bell-icon {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--zs-color-danger, #ef4444);
  color: white;
  font-size: 0.625rem;
  font-weight: 600;
  border-radius: var(--zs-radius-pill);
  line-height: 1;
}

.notification-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  box-shadow: var(--zs-shadow-md);
  overflow: hidden;
  z-index: 100;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--zs-space-3) var(--zs-space-4);
  border-bottom: 1px solid var(--zs-color-border);
}

.panel-title {
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
}

.panel-unread {
  font-size: 0.75rem;
  color: var(--zs-color-primary);
  font-weight: 500;
}

.panel-loading,
.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--zs-space-6);
  color: var(--zs-color-text-muted);
  font-size: 0.875rem;
}

.empty-icon {
  margin: 0 0 var(--zs-space-2);
  color: var(--zs-color-border-strong);
  font-family: Georgia, serif;
  font-size: 1.5rem;
}

.announcement-list {
  flex: 1;
  overflow-y: auto;
  margin: 0;
  padding: 0;
  list-style: none;
}

.announcement-item {
  padding: var(--zs-space-3) var(--zs-space-4);
  border-bottom: 1px solid var(--zs-color-border-soft);
  cursor: pointer;
  transition: background 0.15s ease;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-item:hover {
  background: var(--zs-color-surface-soft);
}

.announcement-item.unread {
  background: var(--zs-color-surface-soft);
}

.item-header {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  margin-bottom: var(--zs-space-1);
}

.severity-dot {
  color: var(--zs-color-text-faint);
  font-size: 0.48rem;
  line-height: 1;
  flex-shrink: 0;
}

.severity-critical {
  color: var(--zs-color-danger);
}

.severity-warning {
  color: var(--zs-color-warning);
}

.severity-success {
  color: var(--zs-color-success);
}

.severity-info {
  color: var(--zs-color-info);
}

.item-title {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding-left: calc(0.5rem + var(--zs-space-2));
}

.severity-label {
  font-size: 0.75rem;
  color: var(--zs-color-text-muted);
}

.item-date {
  font-size: 0.75rem;
  color: var(--zs-color-text-faint);
}

.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.2s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 720px) {
  .notification-panel {
    position: fixed;
    top: auto;
    bottom: 80px;
    right: var(--zs-space-4);
    left: var(--zs-space-4);
    width: auto;
  }
}
</style>

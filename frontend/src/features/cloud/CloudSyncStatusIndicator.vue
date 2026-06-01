<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { cloudSyncManager, type CloudSyncManagerState } from './cloudSyncManager'
import { deriveCloudSyncViewState } from './cloudSyncStatusView'

const state = ref<CloudSyncManagerState>(cloudSyncManager.getState())
const isOnline = ref(navigator.onLine)

let unsub: (() => void) | null = null

onMounted(() => {
  unsub = cloudSyncManager.onStateChange((newState) => {
    state.value = newState
  })
  window.addEventListener('online', handleOnlineChange)
  window.addEventListener('offline', handleOnlineChange)
})

onUnmounted(() => {
  if (unsub) unsub()
  window.removeEventListener('online', handleOnlineChange)
  window.removeEventListener('offline', handleOnlineChange)
})

function handleOnlineChange() {
  isOnline.value = navigator.onLine
}

const viewState = computed(() => deriveCloudSyncViewState(state.value, isOnline.value))

function handleRetry() {
  cloudSyncManager.retrySync()
}
</script>

<template>
  <span class="sync-status-pill" :class="viewState.tone" :title="viewState.description">
    <span class="sync-dot" />
    {{ viewState.label }}
    <span v-if="viewState.pendingCountLabel" class="sync-pending-count">
      ({{ viewState.pendingCountLabel }})
    </span>
    <button
      v-if="viewState.canRetry"
      class="sync-retry-btn"
      :disabled="state.syncing"
      aria-label="重试云同步"
      title="重试同步"
      @click.stop="handleRetry"
    >
      {{ state.syncing ? '同步中…' : '重试' }}
    </button>
  </span>
</template>

<style scoped>
.sync-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.success {
  background: var(--zs-color-success-soft, #e8f5e9);
  color: var(--zs-color-success, #2e7d32);
}
.success .sync-dot {
  background: var(--zs-color-success, #2e7d32);
}

.info {
  background: var(--zs-color-info-soft, #e3f2fd);
  color: var(--zs-color-info, #1565c0);
}
.info .sync-dot {
  background: var(--zs-color-info, #1565c0);
  animation: pulse 1s infinite;
}

.warning {
  background: var(--zs-color-warning-soft, #fff8e1);
  color: var(--zs-color-warning, #f57f17);
}
.warning .sync-dot {
  background: var(--zs-color-warning, #f57f17);
}

.danger {
  background: var(--zs-color-danger-soft, #fce4ec);
  color: var(--zs-color-danger, #c62828);
}
.danger .sync-dot {
  background: var(--zs-color-danger, #c62828);
}

.muted {
  background: var(--zs-color-surface-muted, #f5f5f5);
  color: var(--zs-color-text-muted, #999);
}
.muted .sync-dot {
  background: var(--zs-color-text-muted, #999);
}

.sync-pending-count {
  font-weight: 400;
  opacity: 0.8;
}

.sync-retry-btn {
  background: none;
  border: 1px solid currentColor;
  border-radius: 4px;
  padding: 0 4px;
  font-size: 0.65rem;
  cursor: pointer;
  color: inherit;
  margin-left: 2px;
  line-height: 1.4;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
</style>

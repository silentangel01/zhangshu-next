/**
 * Pure function that derives a cloud sync view state from the raw manager state
 * and browser online status. No API calls, no Vue lifecycle dependencies.
 *
 * The `synced` kind requires ALL of:
 *   - cloudLoggedIn === true
 *   - cloudEnabled === true
 *   - isOnline === true
 *   - pendingCount === 0
 *   - syncing === false
 *   - status !== 'error' && lastError === null
 *   - conflictCount === 0
 *   - lastSyncAt !== null (at least one trusted sync completed)
 */

import type { CloudSyncManagerState } from './cloudSyncManager'

export type CloudSyncViewKind =
  | 'disabled'
  | 'local_only'
  | 'pending'
  | 'syncing'
  | 'synced'
  | 'offline'
  | 'offline_with_pending'
  | 'error'
  | 'conflict'
  | 'unknown'

export type CloudSyncViewTone = 'success' | 'info' | 'warning' | 'danger' | 'muted'

export interface CloudSyncViewState {
  kind: CloudSyncViewKind
  label: string
  description: string
  tone: CloudSyncViewTone
  canRetry: boolean
  pendingCountLabel: string | null
}

export function deriveCloudSyncViewState(
  state: CloudSyncManagerState,
  isOnline: boolean,
): CloudSyncViewState {
  // 1. Not logged in or cloud not enabled → disabled
  if (!state.cloudLoggedIn || !state.cloudEnabled) {
    return {
      kind: 'disabled',
      label: '云同步未启用',
      description: '请在项目设置中启用云同步',
      tone: 'muted',
      canRetry: false,
      pendingCountLabel: null,
    }
  }

  // 2. Offline states
  if (!isOnline) {
    if (state.pendingCount > 0) {
      return {
        kind: 'offline_with_pending',
        label: '离线，已保存到本机，联网后同步',
        description: `当前有 ${state.pendingCount} 条更改保存在本机，等待联网后上传`,
        tone: 'muted',
        canRetry: false,
        pendingCountLabel: `${state.pendingCount} 条待同步`,
      }
    }
    return {
      kind: 'offline',
      label: '离线',
      description: '当前无网络连接',
      tone: 'muted',
      canRetry: false,
      pendingCountLabel: null,
    }
  }

  // 3. Currently syncing
  if (state.syncing) {
    return {
      kind: 'syncing',
      label: '同步中',
      description: '正在与云端同步数据',
      tone: 'info',
      canRetry: false,
      pendingCountLabel: null,
    }
  }

  // 4. Error state
  if (state.status === 'error' || state.lastError) {
    const errorDetail = state.lastError || '未知错误'
    return {
      kind: 'error',
      label: '同步失败',
      description: `${errorDetail}。本机内容已保留，可点击重试`,
      tone: 'danger',
      canRetry: true,
      pendingCountLabel: state.pendingCount > 0 ? `${state.pendingCount} 条待同步` : null,
    }
  }

  // 5. Conflict state
  if (state.status === 'has_conflicts' || state.conflictCount > 0) {
    return {
      kind: 'conflict',
      label: '部分内容存在多设备修改',
      description: `${state.conflictCount} 处内容在多台设备上同时修改，请在备份面板中查看`,
      tone: 'warning',
      canRetry: false,
      pendingCountLabel: null,
    }
  }

  // 6. Pending changes waiting for debounce
  if (state.pendingCount > 0) {
    return {
      kind: 'pending',
      label: '等待同步',
      description: `${state.pendingCount} 条更改将在停止编辑后自动同步`,
      tone: 'warning',
      canRetry: false,
      pendingCountLabel: `${state.pendingCount} 条待同步`,
    }
  }

  // 7. Synced — requires all conditions met
  if (state.lastSyncAt) {
    return {
      kind: 'synced',
      label: '已同步至云端',
      description: `上次同步：${formatSyncTime(state.lastSyncAt)}`,
      tone: 'success',
      canRetry: false,
      pendingCountLabel: null,
    }
  }

  // 8. Fallback: enabled and online but no sync has ever completed
  return {
    kind: 'local_only',
    label: '已连接，等待首次同步',
    description: '云同步已启用，等待首次同步完成',
    tone: 'info',
    canRetry: false,
    pendingCountLabel: null,
  }
}

function formatSyncTime(isoString: string): string {
  try {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin} 分钟前`
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return `${diffHour} 小时前`
    return date.toLocaleDateString('zh-CN')
  } catch {
    return isoString
  }
}

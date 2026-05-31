/**
 * Cloud sync manager — manages periodic sync polling and auto-trigger.
 *
 * - Polls sync status every 5 seconds.
 * - Triggers runCloudSync() when pending_count > 0 and last dirty > 15s.
 * - Prevents concurrent sync runs.
 * - Pauses when navigator.onLine === false.
 * - Resumes on window 'online' event with 5s delay.
 */

import { getCloudSyncStatus, runCloudSync } from '@/entities/cloud/api'

const POLL_INTERVAL_MS = 5_000
const DEBOUNCE_MS = 15_000
const ONLINE_DELAY_MS = 5_000
const RETRY_THROTTLE_MS = 3_000

export interface CloudSyncManagerState {
  status: string
  pendingCount: number
  syncing: boolean
  lastError: string | null
  lastSyncAt: string | null
  cloudLoggedIn: boolean
  cloudEnabled: boolean
  autoSyncEnabled: boolean
  cloudProjectId: string | null
  lastStatusCheckedAt: string | null
  conflictCount: number
}

export class CloudSyncManager {
  private projectId: string | null = null
  private pollTimer: ReturnType<typeof setInterval> | null = null
  private onlineTimer: ReturnType<typeof setTimeout> | null = null
  private syncing = false
  private state: CloudSyncManagerState = {
    status: 'idle',
    pendingCount: 0,
    syncing: false,
    lastError: null,
    lastSyncAt: null,
    cloudLoggedIn: false,
    cloudEnabled: false,
    autoSyncEnabled: true,
    cloudProjectId: null,
    lastStatusCheckedAt: null,
    conflictCount: 0,
  }
  private listeners: Array<(state: CloudSyncManagerState) => void> = []
  private lastDirtyAt = 0
  private lastRetryAt = 0
  private initialSyncDone = false

  getState(): CloudSyncManagerState {
    return { ...this.state }
  }

  onStateChange(listener: (state: CloudSyncManagerState) => void): () => void {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener)
    }
  }

  private notify(): void {
    const snapshot = this.getState()
    for (const listener of this.listeners) {
      listener(snapshot)
    }
  }

  start(projectId: string): void {
    if (this.projectId === projectId && this.pollTimer) {
      return
    }
    this.stop()
    this.projectId = projectId
    this.syncing = false
    this.lastDirtyAt = Date.now()
    this.lastRetryAt = 0
    this.initialSyncDone = false

    // Listen for online/offline events
    window.addEventListener('online', this.handleOnline)
    window.addEventListener('offline', this.handleOffline)

    // Start polling
    void this.poll()
    this.pollTimer = setInterval(() => {
      void this.poll()
    }, POLL_INTERVAL_MS)
  }

  stop(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
    if (this.onlineTimer) {
      clearTimeout(this.onlineTimer)
      this.onlineTimer = null
    }
    window.removeEventListener('online', this.handleOnline)
    window.removeEventListener('offline', this.handleOffline)
    this.projectId = null
    this.syncing = false
    this.initialSyncDone = false
  }

  notifyDirty(projectId?: string): void {
    if (projectId !== undefined && projectId !== this.projectId) {
      return
    }
    this.lastDirtyAt = Date.now()
  }

  private handleOnline = (): void => {
    if (this.onlineTimer) {
      clearTimeout(this.onlineTimer)
    }
    this.onlineTimer = setTimeout(() => {
      this.onlineTimer = null
      if (this.projectId) {
        void this.triggerSync()
      }
    }, ONLINE_DELAY_MS)
  }

  private handleOffline = (): void => {
    // Nothing to do — poll() will skip when offline
  }

  private async poll(): Promise<void> {
    if (!this.projectId || !navigator.onLine) {
      return
    }

    try {
      const status = await getCloudSyncStatus(this.projectId)
      this.state.pendingCount = status.pending_count
      this.state.lastError = status.last_error
      this.state.lastSyncAt = status.last_sync_at
      this.state.status = status.status
      this.state.cloudLoggedIn = status.cloud_logged_in
      this.state.cloudEnabled = status.cloud_enabled
      this.state.autoSyncEnabled = status.auto_sync_enabled
      this.state.cloudProjectId = status.cloud_project_id
      this.state.lastStatusCheckedAt = new Date().toISOString()

      if (!status.cloud_logged_in || !status.cloud_enabled) {
        this.notify()
        return
      }

      // Initial sync on first successful status after start()
      if (!this.initialSyncDone) {
        this.initialSyncDone = true
        if (!this.syncing && navigator.onLine) {
          void this.triggerSync()
        }
        this.notify()
        return
      }

      // Auto-trigger sync if there are pending changes and debounce has elapsed
      if (status.pending_count > 0 && !this.syncing) {
        const elapsed = Date.now() - this.lastDirtyAt
        if (elapsed >= DEBOUNCE_MS) {
          void this.triggerSync()
        }
      }

      this.notify()
    } catch {
      // Network error — skip this poll
    }
  }

  private async triggerSync(): Promise<void> {
    if (!this.projectId || this.syncing || !navigator.onLine) {
      return
    }

    this.syncing = true
    this.state.syncing = true
    this.state.status = 'syncing'
    this.notify()

    try {
      const result = await runCloudSync(this.projectId)
      if (result.errors.length === 0) {
        this.state.pendingCount = 0
      }
      this.state.lastError = result.errors.length > 0 ? result.errors.join('; ') : null
      this.state.lastSyncAt = new Date().toISOString()
      this.state.status = result.conflicts > 0 ? 'has_conflicts' : 'idle'
      this.state.conflictCount = result.conflicts
    } catch (error) {
      this.state.lastError = error instanceof Error ? error.message : '同步失败'
      this.state.status = 'error'
      this.state.conflictCount = 0
    } finally {
      this.syncing = false
      this.state.syncing = false
      this.notify()
    }
  }

  retrySync(): void {
    if (!this.projectId || this.syncing || !navigator.onLine) return
    const now = Date.now()
    if (now - this.lastRetryAt < RETRY_THROTTLE_MS) return
    this.lastRetryAt = now
    this.state.lastError = null
    this.state.status = 'idle'
    this.state.conflictCount = 0
    this.notify()
    void this.triggerSync()
  }
}

// Singleton instance
export const cloudSyncManager = new CloudSyncManager()

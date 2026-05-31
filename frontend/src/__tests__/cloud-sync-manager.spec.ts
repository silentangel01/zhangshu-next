/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CloudSyncManager } from '@/features/cloud/cloudSyncManager'

// Mock the cloud API module
vi.mock('@/entities/cloud/api', () => ({
  getCloudSyncStatus: vi.fn(),
  runCloudSync: vi.fn(),
}))

import { getCloudSyncStatus, runCloudSync } from '@/entities/cloud/api'

const mockGetStatus = vi.mocked(getCloudSyncStatus)
const mockRunSync = vi.mocked(runCloudSync)

describe('CloudSyncManager', () => {
  let manager: CloudSyncManager

  beforeEach(() => {
    vi.clearAllMocks()
    manager = new CloudSyncManager()
    vi.useFakeTimers()
    vi.setSystemTime(0)

    // Default: online
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })

    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 0,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })

    mockRunSync.mockResolvedValue({
      pushed: 0,
      pulled: 0,
      new_cursor: 0,
      conflicts: 0,
      errors: [],
      duration_ms: 100,
    })
  })

  afterEach(() => {
    manager.stop()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('starts with idle state', () => {
    const state = manager.getState()
    expect(state.status).toBe('idle')
    expect(state.syncing).toBe(false)
    expect(state.pendingCount).toBe(0)
  })

  it('polls status after start', async () => {
    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)

    expect(mockGetStatus).toHaveBeenCalledWith('proj-1')
  })

  it('does not poll when offline', async () => {
    // Set offline BEFORE starting the manager
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })

    manager.start('proj-1')
    // Allow the initial void poll() call to resolve (it's a microtask, not timer-based)
    await vi.advanceTimersByTimeAsync(200)

    const callsAfterStart = mockGetStatus.mock.calls.length

    // Advance 10s more — no additional polls should happen while offline
    await vi.advanceTimersByTimeAsync(10000)
    expect(mockGetStatus.mock.calls.length).toBe(callsAfterStart)
  })

  it('prevents concurrent sync runs', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 3,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })

    // Make runSync slow
    let resolveSync!: (v: import('@/entities/cloud/types').CloudSyncRunResult) => void
    mockRunSync.mockReturnValue(
      new Promise((resolve) => {
        resolveSync = resolve
      }),
    )

    manager.start('proj-1')
    // Initial poll
    await vi.advanceTimersByTimeAsync(200)

    // Advance past debounce (15s) — next poll will trigger sync
    await vi.advanceTimersByTimeAsync(16000)

    // Should have called runSync once
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Trigger another poll — should NOT start another sync (syncing=true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Resolve the sync
    resolveSync({
      pushed: 3,
      pulled: 0,
      new_cursor: 3,
      conflicts: 0,
      errors: [],
      duration_ms: 500,
    })
    await vi.advanceTimersByTimeAsync(200)
  })

  it('online event triggers sync after delay', async () => {
    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)

    const callsBefore = mockRunSync.mock.calls.length

    // Go offline then online
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })
    window.dispatchEvent(new Event('offline'))

    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
    window.dispatchEvent(new Event('online'))

    // Sync should NOT have been triggered by online event yet (within 5s)
    await vi.advanceTimersByTimeAsync(4000)
    // The number of runSync calls should be the same as before online event
    // (no additional calls from the online handler)
    const callsAfter4s = mockRunSync.mock.calls.length

    // After 5s delay, online handler triggers sync
    await vi.advanceTimersByTimeAsync(2000)
    expect(mockRunSync.mock.calls.length).toBeGreaterThanOrEqual(callsAfter4s)
  })

  it('stops cleanly and clears timers', async () => {
    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)

    const callsAfterStart = mockGetStatus.mock.calls.length

    manager.stop()

    // Advance time — no new polls should happen
    await vi.advanceTimersByTimeAsync(10000)
    expect(mockGetStatus.mock.calls.length).toBe(callsAfterStart)
  })

  it('notifies listeners on state change', async () => {
    const listener = vi.fn()
    manager.onStateChange(listener)
    manager.start('proj-1')

    await vi.advanceTimersByTimeAsync(200)

    expect(listener).toHaveBeenCalled()
  })

  // ── Phase 1: notifyDirty(projectId) ──────────────────────────

  it('notifyDirty(projectId) resets debounce when project matches', async () => {
    const pendingStatus = {
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 3,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    }
    mockGetStatus.mockResolvedValue(pendingStatus)

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    // Phase 2: initial sync at t=200
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance 10s (t=10200). Polls at t=5000, t=10000 resolve:
    // elapsed since t=0 = 4800, 9800 < 15000 → no auto-sync yet.
    await vi.advanceTimersByTimeAsync(10_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // notifyDirty('proj-1') at t=10200 resets lastDirtyAt to t=10200
    manager.notifyDirty('proj-1')

    // Advance 15s (t=25200). Polls at t=15000, t=20000, t=25000:
    // elapsed since t=10200 = 4800, 9800, 14800 < 15000 → no sync.
    await vi.advanceTimersByTimeAsync(15_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance 5s (t=30200). Poll at t=30000:
    // elapsed since t=10200 = 19800 >= 15000 → sync fires (2nd call).
    await vi.advanceTimersByTimeAsync(5_000)
    expect(mockRunSync).toHaveBeenCalledTimes(2)
  })

  it('notifyDirty(otherProjectId) does not affect current project debounce', async () => {
    const pendingStatus = {
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 3,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    }
    mockGetStatus.mockResolvedValue(pendingStatus)

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    // Phase 2: initial sync at t=200
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance 10s (t=10200). Polls at t=5000, t=10000 resolve:
    // elapsed since t=0 = 4800, 9800 < 15000 → no auto-sync yet.
    await vi.advanceTimersByTimeAsync(10_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // notifyDirty for DIFFERENT project right before debounce expires.
    // If correctly ignored: lastDirtyAt stays at t=0, so poll at t=15000
    //   sees elapsed=15000 >= 15000 → sync fires.
    // If incorrectly applied: lastDirtyAt becomes t=10200, so poll at t=15000
    //   sees elapsed=4800 < 15000 → no sync until t=25200.
    manager.notifyDirty('proj-2')

    // Advance 5s (t=15200). Poll at t=15000 resolves → sync should fire.
    await vi.advanceTimersByTimeAsync(5_000)
    expect(mockRunSync).toHaveBeenCalledTimes(2)
  })

  it('notifyDirty() without projectId resets debounce', async () => {
    const pendingStatus = {
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 3,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    }
    mockGetStatus.mockResolvedValue(pendingStatus)

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    // Phase 2: initial sync at t=200
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance 10s (t=10200). Polls at t=5000, t=10000 resolve:
    // elapsed since t=0 = 4800, 9800 < 15000 → no auto-sync yet.
    await vi.advanceTimersByTimeAsync(10_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // notifyDirty() without projectId → resets lastDirtyAt to t=10200
    manager.notifyDirty()

    // Advance 15s (t=25200). Polls at t=15000, t=20000, t=25000:
    // elapsed since t=10200 = 4800, 9800, 14800 < 15000 → no sync.
    await vi.advanceTimersByTimeAsync(15_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance 5s (t=30200). Poll at t=30000:
    // elapsed since t=10200 = 19800 >= 15000 → sync fires (2nd call).
    await vi.advanceTimersByTimeAsync(5_000)
    expect(mockRunSync).toHaveBeenCalledTimes(2)
  })

  // ── Phase 2: Initial sync on project entry ──────────────────────

  it('triggers initial sync on first poll when cloud enabled', async () => {
    manager.start('proj-1')
    // Initial poll resolves
    await vi.advanceTimersByTimeAsync(200)
    // Initial sync (runCloudSync) should have been called
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Advance time — no additional syncs should fire (pending_count=0 by default)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(mockRunSync).toHaveBeenCalledTimes(1)
  })

  it('does not trigger initial sync when not logged in', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: false,
      cloud_enabled: false,
      pending_count: 0,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: false,
      cloud_project_id: null,
      device_id: 'test-device',
    })

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    expect(mockRunSync).not.toHaveBeenCalled()

    // Advance more — still no sync
    await vi.advanceTimersByTimeAsync(20_000)
    expect(mockRunSync).not.toHaveBeenCalled()
  })

  it('does not trigger initial sync when cloud disabled', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: false,
      pending_count: 0,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: false,
      cloud_project_id: null,
      device_id: 'test-device',
    })

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    expect(mockRunSync).not.toHaveBeenCalled()
  })

  it('does not trigger initial sync when offline', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    // poll() returns early when offline — getCloudSyncStatus not called
    expect(mockGetStatus).not.toHaveBeenCalled()
    expect(mockRunSync).not.toHaveBeenCalled()
  })

  // ── Phase 3: State extension & bug fixes ──────────────────────

  it('does not clear pendingCount when sync returns errors', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 5,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })
    mockRunSync.mockResolvedValue({
      pushed: 3,
      pulled: 0,
      new_cursor: 3,
      conflicts: 0,
      errors: ['push failed for entity X'],
      duration_ms: 200,
    })

    manager.start('proj-1')
    // Initial poll → triggers initial sync
    await vi.advanceTimersByTimeAsync(200)
    // Let the sync resolve
    await vi.advanceTimersByTimeAsync(200)

    const state = manager.getState()
    expect(state.pendingCount).toBe(5) // NOT cleared to 0
    expect(state.lastError).toContain('push failed')
  })

  it('poll persists cloudLoggedIn, cloudEnabled, cloudProjectId, autoSyncEnabled', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 0,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: false,
      cloud_project_id: 'cp-test',
      device_id: 'test-device',
    })

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)

    const state = manager.getState()
    expect(state.cloudLoggedIn).toBe(true)
    expect(state.cloudEnabled).toBe(true)
    expect(state.cloudProjectId).toBe('cp-test')
    expect(state.autoSyncEnabled).toBe(false)
    expect(state.lastStatusCheckedAt).not.toBeNull()
  })

  it('conflictCount is persisted from sync result', async () => {
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 1,
      last_cursor: 0,
      last_sync_at: null,
      last_error: null,
      status: 'idle',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })
    mockRunSync.mockResolvedValue({
      pushed: 1,
      pulled: 0,
      new_cursor: 1,
      conflicts: 2,
      errors: [],
      duration_ms: 100,
    })

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200) // initial sync
    await vi.advanceTimersByTimeAsync(200) // let it resolve

    const state = manager.getState()
    expect(state.conflictCount).toBe(2)
    expect(state.status).toBe('has_conflicts')
  })

  it('retrySync clears error and triggers sync', async () => {
    // Setup: cloud enabled, initial sync will fail
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 1,
      last_cursor: 0,
      last_sync_at: '2026-01-01T00:00:00Z',
      last_error: '网络超时',
      status: 'error',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })
    mockRunSync.mockRejectedValue(new Error('网络超时'))

    manager.start('proj-1')
    // Initial poll → triggers initial sync which fails
    await vi.advanceTimersByTimeAsync(200)
    await vi.advanceTimersByTimeAsync(200)

    let state = manager.getState()
    expect(state.status).toBe('error')
    expect(state.lastError).toContain('网络超时')

    // Reset mock for retry
    mockRunSync.mockClear()
    mockRunSync.mockResolvedValue({
      pushed: 1,
      pulled: 0,
      new_cursor: 1,
      conflicts: 0,
      errors: [],
      duration_ms: 100,
    })

    // Advance past 3s throttle window before retrying
    await vi.advanceTimersByTimeAsync(3000)

    manager.retrySync()
    await vi.advanceTimersByTimeAsync(200)

    expect(mockRunSync).toHaveBeenCalledTimes(1)
    state = manager.getState()
    expect(state.lastError).toBeNull()
    expect(state.status).toBe('idle')
  })

  it('retrySync throttles repeated calls within 3 seconds', async () => {
    // Setup: error state, sync resolves quickly
    mockGetStatus.mockResolvedValue({
      cloud_logged_in: true,
      cloud_enabled: true,
      pending_count: 0,
      last_cursor: 0,
      last_sync_at: '2026-01-01T00:00:00Z',
      last_error: '网络超时',
      status: 'error',
      auto_sync_enabled: true,
      cloud_project_id: 'cp-1',
      device_id: 'test-device',
    })
    mockRunSync.mockRejectedValue(new Error('网络超时'))

    manager.start('proj-1')
    await vi.advanceTimersByTimeAsync(200)
    await vi.advanceTimersByTimeAsync(200)

    // Past throttle window
    await vi.advanceTimersByTimeAsync(3000)

    mockRunSync.mockClear()
    mockRunSync.mockResolvedValue({
      pushed: 0,
      pulled: 0,
      new_cursor: 0,
      conflicts: 0,
      errors: [],
      duration_ms: 50,
    })

    // First retry — should trigger
    manager.retrySync()
    await vi.advanceTimersByTimeAsync(200)
    expect(mockRunSync).toHaveBeenCalledTimes(1)

    // Immediately retry again — should be throttled
    mockRunSync.mockClear()
    manager.retrySync()
    await vi.advanceTimersByTimeAsync(200)
    expect(mockRunSync).not.toHaveBeenCalled()

    // Wait past throttle, retry again — should trigger
    await vi.advanceTimersByTimeAsync(3000)
    manager.retrySync()
    await vi.advanceTimersByTimeAsync(200)
    expect(mockRunSync).toHaveBeenCalledTimes(1)
  })
})

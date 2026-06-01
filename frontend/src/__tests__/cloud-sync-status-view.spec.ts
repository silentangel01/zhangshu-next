import { describe, expect, it } from 'vitest'

import type { CloudSyncManagerState } from '@/features/cloud/cloudSyncManager'
import { deriveCloudSyncViewState } from '@/features/cloud/cloudSyncStatusView'

function makeState(overrides: Partial<CloudSyncManagerState> = {}): CloudSyncManagerState {
  return {
    status: 'idle',
    pendingCount: 0,
    syncing: false,
    lastError: null,
    lastSyncAt: null,
    cloudLoggedIn: true,
    cloudEnabled: true,
    autoSyncEnabled: true,
    cloudProjectId: 'cp-1',
    lastStatusCheckedAt: '2026-05-31T10:00:00Z',
    conflictCount: 0,
    tokenExpired: false,
    ...overrides,
  }
}

describe('deriveCloudSyncViewState', () => {
  // ── token_expired ─────────────────────────────

  it('returns token_expired when tokenExpired is true', () => {
    const view = deriveCloudSyncViewState(
      makeState({ tokenExpired: true, cloudLoggedIn: false }),
      true,
    )
    expect(view.kind).toBe('token_expired')
    expect(view.label).toContain('登录已过期')
    expect(view.tone).toBe('danger')
    expect(view.canRetry).toBe(false)
  })

  it('token_expired takes priority over disabled', () => {
    const view = deriveCloudSyncViewState(
      makeState({ tokenExpired: true, cloudLoggedIn: false, cloudEnabled: false }),
      true,
    )
    expect(view.kind).toBe('token_expired')
  })

  // ── disabled ──────────────────────────────────

  it('returns disabled when not logged in', () => {
    const view = deriveCloudSyncViewState(makeState({ cloudLoggedIn: false }), true)
    expect(view.kind).toBe('disabled')
    expect(view.tone).toBe('muted')
    expect(view.canRetry).toBe(false)
    expect(view.label).toContain('未启用')
  })

  it('returns disabled when cloud not enabled', () => {
    const view = deriveCloudSyncViewState(makeState({ cloudEnabled: false }), true)
    expect(view.kind).toBe('disabled')
    expect(view.tone).toBe('muted')
  })

  // ── offline ───────────────────────────────────

  it('returns offline_with_pending when offline and pendingCount > 0', () => {
    const view = deriveCloudSyncViewState(makeState({ pendingCount: 5 }), false)
    expect(view.kind).toBe('offline_with_pending')
    expect(view.label).toContain('离线')
    expect(view.label).toContain('本机')
    expect(view.pendingCountLabel).toBe('5 条待同步')
    expect(view.tone).toBe('muted')
  })

  it('returns offline when offline and pendingCount === 0', () => {
    const view = deriveCloudSyncViewState(makeState({ pendingCount: 0 }), false)
    expect(view.kind).toBe('offline')
    expect(view.label).toBe('离线')
    expect(view.pendingCountLabel).toBeNull()
  })

  it('NEVER shows synced when offline', () => {
    const view = deriveCloudSyncViewState(
      makeState({ lastSyncAt: '2026-05-31T10:00:00Z', pendingCount: 0 }),
      false,
    )
    expect(view.kind).not.toBe('synced')
    expect(view.label).not.toContain('云端')
  })

  // ── syncing ───────────────────────────────────

  it('returns syncing when state.syncing is true', () => {
    const view = deriveCloudSyncViewState(makeState({ syncing: true }), true)
    expect(view.kind).toBe('syncing')
    expect(view.tone).toBe('info')
    expect(view.label).toBe('同步中')
  })

  // ── error ─────────────────────────────────────

  it('returns error when status is error', () => {
    const view = deriveCloudSyncViewState(
      makeState({ status: 'error', lastError: '网络超时' }),
      true,
    )
    expect(view.kind).toBe('error')
    expect(view.description).toContain('网络超时')
    expect(view.description).toContain('本机内容已保留')
    expect(view.canRetry).toBe(true)
    expect(view.tone).toBe('danger')
  })

  it('returns error when lastError is set even if status is idle', () => {
    const view = deriveCloudSyncViewState(
      makeState({ status: 'idle', lastError: '认证失败' }),
      true,
    )
    expect(view.kind).toBe('error')
    expect(view.canRetry).toBe(true)
    expect(view.description).toContain('认证失败')
  })

  // ── conflict ──────────────────────────────────

  it('returns conflict when status is has_conflicts', () => {
    const view = deriveCloudSyncViewState(
      makeState({ status: 'has_conflicts', conflictCount: 3 }),
      true,
    )
    expect(view.kind).toBe('conflict')
    expect(view.label).toContain('多设备修改')
    expect(view.description).toContain('3')
    expect(view.tone).toBe('warning')
  })

  it('returns conflict when conflictCount > 0 even if status is idle', () => {
    const view = deriveCloudSyncViewState(
      makeState({ status: 'idle', conflictCount: 1 }),
      true,
    )
    expect(view.kind).toBe('conflict')
  })

  // ── pending ───────────────────────────────────

  it('returns pending when pendingCount > 0 and online', () => {
    const view = deriveCloudSyncViewState(makeState({ pendingCount: 2 }), true)
    expect(view.kind).toBe('pending')
    expect(view.pendingCountLabel).toBe('2 条待同步')
    expect(view.tone).toBe('warning')
    expect(view.label).toContain('等待同步')
  })

  // ── synced ────────────────────────────────────

  it('returns synced when all conditions met', () => {
    const view = deriveCloudSyncViewState(
      makeState({ lastSyncAt: '2026-05-31T10:00:00Z', pendingCount: 0 }),
      true,
    )
    expect(view.kind).toBe('synced')
    expect(view.label).toBe('已同步至云端')
    expect(view.tone).toBe('success')
    expect(view.canRetry).toBe(false)
  })

  it('does NOT return synced when lastSyncAt is null', () => {
    const view = deriveCloudSyncViewState(makeState({ lastSyncAt: null }), true)
    expect(view.kind).not.toBe('synced')
    expect(view.kind).toBe('local_only')
  })

  // ── priority order ────────────────────────────

  it('disabled takes priority over offline', () => {
    const view = deriveCloudSyncViewState(makeState({ cloudEnabled: false }), false)
    expect(view.kind).toBe('disabled')
  })

  it('syncing takes priority over pending', () => {
    const view = deriveCloudSyncViewState(makeState({ syncing: true, pendingCount: 5 }), true)
    expect(view.kind).toBe('syncing')
  })

  it('error takes priority over conflict', () => {
    const view = deriveCloudSyncViewState(
      makeState({ status: 'error', lastError: 'err', conflictCount: 3 }),
      true,
    )
    expect(view.kind).toBe('error')
  })
})

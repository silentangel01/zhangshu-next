/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

// Use vi.hoisted() so these are available inside vi.mock factory
const { _state, _listeners, retrySync, defaultState } = vi.hoisted(() => {
  interface TestState {
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
  const defaultState: TestState = {
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
  }
  return {
    _state: { ...defaultState },
    _listeners: [] as Array<(s: unknown) => void>,
    retrySync: vi.fn(),
    defaultState,
  }
})

vi.mock('@/features/cloud/cloudSyncManager', () => ({
  cloudSyncManager: {
    getState: () => ({ ..._state }),
    onStateChange: (fn: (s: unknown) => void) => {
      _listeners.push(fn)
      return () => {
        const idx = _listeners.indexOf(fn)
        if (idx >= 0) _listeners.splice(idx, 1)
      }
    },
    retrySync,
  },
}))

import CloudSyncStatusIndicator from '@/features/cloud/CloudSyncStatusIndicator.vue'

function setState(overrides: Partial<typeof defaultState>) {
  Object.assign(_state, { ...defaultState, ...overrides })
  for (const fn of _listeners) fn({ ..._state })
}

describe('CloudSyncStatusIndicator', () => {
  beforeEach(() => {
    Object.assign(_state, defaultState)
    _listeners.length = 0
    retrySync.mockClear()
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
  })

  afterEach(() => {
    _listeners.length = 0
  })

  it('shows retry button in error state', async () => {
    setState({ status: 'error', lastError: '网络超时' })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    const retryBtn = wrapper.find('.sync-retry-btn')
    expect(retryBtn.exists()).toBe(true)
    expect(retryBtn.text()).toContain('重试')
  })

  it('clicking retry calls cloudSyncManager.retrySync()', async () => {
    setState({ status: 'error', lastError: '网络超时' })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    const retryBtn = wrapper.find('.sync-retry-btn')
    await retryBtn.trigger('click')

    expect(retrySync).toHaveBeenCalledTimes(1)
  })

  it('syncing state shows syncing label, no retry button', async () => {
    setState({ syncing: true, status: 'syncing' })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    const retryBtn = wrapper.find('.sync-retry-btn')
    expect(retryBtn.exists()).toBe(false)
    expect(wrapper.text()).toContain('同步中')
  })

  it('synced state does not show retry button', async () => {
    setState({ lastSyncAt: '2026-05-31T10:00:00Z', pendingCount: 0 })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    const retryBtn = wrapper.find('.sync-retry-btn')
    expect(retryBtn.exists()).toBe(false)
    expect(wrapper.text()).toContain('已同步至云端')
  })

  it('offline with pending shows count label', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })
    setState({ pendingCount: 3 })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    expect(wrapper.text()).toContain('离线')
    expect(wrapper.text()).toContain('3 条待同步')
    expect(wrapper.text()).toContain('本机')
  })

  it('disabled state does not show synced', async () => {
    setState({ cloudEnabled: false })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    expect(wrapper.text()).toContain('云同步未启用')
    expect(wrapper.text()).not.toContain('已同步')
  })

  it('updates when manager state changes', async () => {
    setState({ lastSyncAt: '2026-05-31T10:00:00Z' })

    const wrapper = mount(CloudSyncStatusIndicator)
    await flushPromises()

    expect(wrapper.text()).toContain('已同步至云端')

    // Simulate state change to error
    setState({ status: 'error', lastError: '断网了' })
    await flushPromises()

    expect(wrapper.text()).toContain('同步失败')
    expect(wrapper.find('.sync-retry-btn').exists()).toBe(true)
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/entities/cloud/api', () => ({
  getCloudAccountSnapshot: vi.fn(),
  refreshCloudAccountSnapshot: vi.fn(),
}))

import {
  getCloudAccountSnapshot,
  refreshCloudAccountSnapshot,
} from '@/entities/cloud/api'
import { useCloudAccountStore } from '@/stores/cloudAccount'
import type { CloudAccountSnapshot } from '@/entities/cloud/types'

const cached: CloudAccountSnapshot = {
  status: {
    logged_in: true,
    cloud_available: true,
    email: 'writer@example.com',
    display_name: '作者',
    phone_number: null,
  },
  profile: {
    id: 'u1',
    email: 'writer@example.com',
    phone_number: null,
    display_name: '作者',
    signature: null,
    avatar_url: null,
    avatar_updated_at: null,
    password_changed_at: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  usage: {
    storage_used_bytes: 0,
    storage_quota_bytes: 1024,
    backup_count: 0,
    backup_count_quota: 100,
    backup_init_used_last_hour: 0,
    backup_init_limit_per_hour: 30,
    max_backup_size_bytes: 512,
  },
  cached_at: '2026-08-09T00:00:00Z',
  cache_state: 'fresh',
  session_state: 'active',
  device: { id: 'device-1', name: '章枢 · 测试电脑' },
  refresh_error: null,
}

describe('cloud account store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(getCloudAccountSnapshot).mockResolvedValue(cached)
    vi.mocked(refreshCloudAccountSnapshot).mockResolvedValue(cached)
  })

  it('hydrates the last local snapshot without contacting the cloud refresh endpoint', async () => {
    const store = useCloudAccountStore()

    await store.hydrate()

    expect(store.profile?.display_name).toBe('作者')
    expect(store.hydrated).toBe(true)
    expect(refreshCloudAccountSnapshot).not.toHaveBeenCalled()
  })

  it('deduplicates concurrent background refresh requests', async () => {
    const store = useCloudAccountStore()

    await Promise.all([store.refresh(), store.refresh(), store.refresh()])

    expect(refreshCloudAccountSnapshot).toHaveBeenCalledTimes(1)
  })
})

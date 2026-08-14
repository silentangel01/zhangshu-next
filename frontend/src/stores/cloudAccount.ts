import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getCloudAccountSnapshot,
  refreshCloudAccountSnapshot,
} from '@/entities/cloud/api'
import type {
  CloudAccountSnapshot,
  CloudAccountStatus,
} from '@/entities/cloud/types'

export const useCloudAccountStore = defineStore('cloud-account', () => {
  const snapshot = ref<CloudAccountSnapshot | null>(null)
  const hydrated = ref(false)
  const refreshing = ref(false)
  const lastError = ref('')
  let hydratePromise: Promise<void> | null = null
  let refreshPromise: Promise<void> | null = null

  const status = computed(() => snapshot.value?.status ?? null)
  const profile = computed(() => snapshot.value?.profile ?? null)
  const usage = computed(() => snapshot.value?.usage ?? null)
  const sessionState = computed(() => snapshot.value?.session_state ?? 'signed_out')

  function assign(next: CloudAccountSnapshot) {
    snapshot.value = next
    lastError.value = next.refresh_error ?? ''
  }

  async function hydrate(force = false): Promise<void> {
    if (hydrated.value && !force) return
    if (hydratePromise) return hydratePromise
    hydratePromise = getCloudAccountSnapshot()
      .then(assign)
      .catch((error: unknown) => {
        lastError.value = error instanceof Error ? error.message : '无法读取本地账户信息。'
      })
      .finally(() => {
        hydrated.value = true
        hydratePromise = null
      })
    return hydratePromise
  }

  async function refresh(): Promise<void> {
    if (refreshPromise) return refreshPromise
    refreshing.value = true
    refreshPromise = refreshCloudAccountSnapshot()
      .then(assign)
      .catch((error: unknown) => {
        lastError.value = error instanceof Error ? error.message : '无法刷新账户信息。'
      })
      .finally(() => {
        refreshing.value = false
        refreshPromise = null
      })
    return refreshPromise
  }

  function applyLogin(nextStatus: CloudAccountStatus) {
    const current = snapshot.value
    snapshot.value = {
      status: nextStatus,
      profile: current?.profile ?? null,
      usage: current?.usage ?? null,
      cached_at: current?.cached_at ?? null,
      cache_state: current?.cache_state ?? 'empty',
      session_state: 'active',
      device: current?.device ?? { id: '', name: '本机' },
      refresh_error: null,
    }
    hydrated.value = true
  }

  function clear() {
    const current = snapshot.value
    snapshot.value = {
      status: {
        logged_in: false,
        cloud_available: current?.status.cloud_available ?? true,
        email: null,
        display_name: null,
        phone_number: null,
      },
      profile: null,
      usage: null,
      cached_at: null,
      cache_state: 'empty',
      session_state: 'signed_out',
      device: current?.device ?? { id: '', name: '本机' },
      refresh_error: null,
    }
    hydrated.value = true
    lastError.value = ''
  }

  return {
    snapshot,
    status,
    profile,
    usage,
    sessionState,
    hydrated,
    refreshing,
    lastError,
    hydrate,
    refresh,
    applyLogin,
    clear,
  }
})

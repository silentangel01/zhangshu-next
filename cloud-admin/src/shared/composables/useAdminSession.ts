import { readonly, ref } from 'vue'
import type { AdminMeResponse } from '@/entities/admin-auth/types'
import { adminMe } from '@/entities/admin-auth/api'

const me = ref<AdminMeResponse | null>(null)
const initialized = ref(false)
let initPromise: Promise<AdminMeResponse | null> | null = null

export function useAdminSession() {
  function hasPermission(permission: string): boolean {
    return me.value?.permissions.includes(permission) ?? false
  }

  function hasAnyPermission(...permissions: string[]): boolean {
    return permissions.some((p) => hasPermission(p))
  }

  /**
   * Ensure the admin session is loaded. Calls /api/admin/auth/me exactly once
   * per page load. Safe to call from router guard and components.
   */
  async function ensureSession(): Promise<AdminMeResponse | null> {
    if (initialized.value) return me.value
    if (!initPromise) {
      initPromise = adminMe()
        .then((res) => {
          me.value = res
          initialized.value = true
          return res
        })
        .catch(() => {
          initialized.value = true
          return null
        })
    }
    return initPromise
  }

  function clearSession() {
    me.value = null
    initialized.value = false
    initPromise = null
  }

  return {
    me: readonly(me),
    initialized: readonly(initialized),
    hasPermission,
    hasAnyPermission,
    ensureSession,
    clearSession,
  }
}

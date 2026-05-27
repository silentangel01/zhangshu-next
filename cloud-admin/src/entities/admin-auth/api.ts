import { apiRequest } from '@/shared/api/client'
import type { AdminLoginRequest, AdminMeResponse } from './types'

export function adminLogin(body: AdminLoginRequest) {
  return apiRequest<AdminMeResponse>('/api/admin/auth/login', {
    method: 'POST',
    body,
  })
}

export function adminLogout() {
  return apiRequest<{ ok: boolean }>('/api/admin/auth/logout', { method: 'POST' })
}

export function adminRefresh() {
  return apiRequest<{ ok: boolean }>('/api/admin/auth/refresh', { method: 'POST' })
}

export function adminMe() {
  return apiRequest<AdminMeResponse>('/api/admin/auth/me')
}

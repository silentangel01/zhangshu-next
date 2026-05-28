import { apiRequest } from '@/shared/api/client'
import type { AdminUserDetail, AdminUserListResponse } from './types'

export function listUsers(params?: {
  keyword?: string
  status?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.status) search.set('status', params.status)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const q = search.toString()
  return apiRequest<AdminUserListResponse>(`/api/admin/users${q ? `?${q}` : ''}`)
}

export function getUserDetail(id: string) {
  return apiRequest<AdminUserDetail>(`/api/admin/users/${id}`)
}

export function toggleUserActive(id: string) {
  return apiRequest<{ id: string; is_active: boolean }>(
    `/api/admin/users/${id}/toggle-active`,
    { method: 'POST' },
  )
}

export function forceLogoutUser(id: string) {
  return apiRequest<{ ok: boolean; tokens_revoked: number }>(
    `/api/admin/users/${id}/force-logout`,
    { method: 'POST' },
  )
}

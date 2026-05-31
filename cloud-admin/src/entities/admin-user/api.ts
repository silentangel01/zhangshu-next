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

export function toggleUserActive(id: string, reason: string) {
  return apiRequest<{ id: string; is_active: boolean; action: string }>(
    `/api/admin/users/${id}/toggle-active`,
    { method: 'POST', body: { reason } },
  )
}

export function forceLogoutUser(id: string, reason: string) {
  return apiRequest<{ ok: boolean; tokens_revoked: number }>(
    `/api/admin/users/${id}/force-logout`,
    { method: 'POST', body: { reason } },
  )
}

export function changeAdminRole(
  userId: string,
  adminRole: string | null,
  reason: string,
  confirmText: string,
) {
  return apiRequest<{ id: string; admin_role: string | null; effective_role: string | null }>(
    `/api/admin/roles/users/${userId}/admin-role`,
    { method: 'PATCH', body: { admin_role: adminRole, reason, confirm_text: confirmText } },
  )
}

export function getPermissionMatrix() {
  return apiRequest<{
    roles: Record<string, string[]>
    current_user_role: string | null
    current_user_permissions: string[]
  }>('/api/admin/roles/permissions')
}

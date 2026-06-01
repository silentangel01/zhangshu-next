import { apiRequest } from '@/shared/api/client'
import type { AuditLogListResponse } from './types'

export function listAuditLogs(params?: {
  event?: string
  userId?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.event) search.set('event', params.event)
  if (params?.userId) search.set('user_id', params.userId)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const q = search.toString()
  return apiRequest<AuditLogListResponse>(`/api/admin/audit${q ? `?${q}` : ''}`)
}

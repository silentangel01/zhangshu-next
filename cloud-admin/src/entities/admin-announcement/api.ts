import { apiRequest } from '@/shared/api/client'
import type {
  Announcement,
  AnnouncementListResponse,
  CreateAnnouncementRequest,
} from './types'

export function listAdminAnnouncements(params?: {
  status?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const q = search.toString()
  return apiRequest<AnnouncementListResponse>(
    `/api/admin/announcements${q ? `?${q}` : ''}`,
  )
}

export function createAnnouncement(body: CreateAnnouncementRequest) {
  return apiRequest<Announcement>('/api/admin/announcements', {
    method: 'POST',
    body,
  })
}

export function publishAnnouncement(id: string) {
  return apiRequest<Announcement>(`/api/admin/announcements/${id}/publish`, {
    method: 'POST',
  })
}

export function archiveAnnouncement(id: string) {
  return apiRequest<Announcement>(`/api/admin/announcements/${id}/archive`, {
    method: 'POST',
  })
}

export function deleteAnnouncement(id: string) {
  return apiRequest<void>(`/api/admin/announcements/${id}`, { method: 'DELETE' })
}

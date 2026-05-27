import { apiRequest } from '@/shared/api/client'
import type {
  Announcement,
  AnnouncementListResponse,
  CreateAnnouncementRequest,
} from './types'

export function listAdminAnnouncements() {
  return apiRequest<AnnouncementListResponse>('/api/admin/announcements')
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

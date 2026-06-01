import { apiRequest } from '@/shared/api/client'

import type { AnnouncementListResponse } from './types'

export function listAnnouncements(
  platform?: string,
  appVersion?: string,
): Promise<AnnouncementListResponse> {
  const params = new URLSearchParams()
  if (platform) params.set('platform', platform)
  if (appVersion) params.set('app_version', appVersion)
  const query = params.toString()
  const path = `/api/cloud/announcements${query ? `?${query}` : ''}`
  return apiRequest<AnnouncementListResponse>(path)
}

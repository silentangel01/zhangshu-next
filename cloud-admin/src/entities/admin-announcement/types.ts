export interface Announcement {
  id: string
  title: string
  body: string
  severity: string
  status: string
  audience: string
  platform: string | null
  min_app_version: string | null
  max_app_version: string | null
  starts_at: string | null
  ends_at: string | null
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface AnnouncementListResponse {
  items: Announcement[]
  total: number
}

export interface CreateAnnouncementRequest {
  title: string
  body: string
  severity?: string
  audience?: string
  platform?: string | null
}

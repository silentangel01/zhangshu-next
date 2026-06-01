export interface Announcement {
  id: string
  title: string
  body: string
  severity: 'info' | 'success' | 'warning' | 'critical'
  published_at: string | null
  starts_at: string | null
  ends_at: string | null
}

export interface AnnouncementListResponse {
  items: Announcement[]
  total: number
  cloud_available: boolean
}

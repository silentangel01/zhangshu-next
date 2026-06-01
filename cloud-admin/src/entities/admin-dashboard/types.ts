export interface DashboardSummary {
  total_users: number
  active_24h: number
  active_7d: number
  active_30d: number
  today_registrations: number
  total_cloud_projects: number
  total_cloud_backups: number
  total_storage_bytes: number
  open_feedback: number
  urgent_feedback: number
}

export interface DailyCount {
  day: string
  count: number
}

export interface ActivitySeries {
  days: number
  daily_active: DailyCount[]
  daily_registrations: DailyCount[]
  daily_feedback: DailyCount[]
  daily_backups: DailyCount[]
}

export interface FeedbackStats {
  by_status: Record<string, number>
  by_category: Record<string, number>
}

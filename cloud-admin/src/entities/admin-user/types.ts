export interface AdminUserListItem {
  id: string
  email: string
  display_name: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  last_login_at: string | null
  last_seen_at: string | null
  login_count: number
  cloud_project_count: number
  cloud_backup_count: number
  feedback_count: number
}

export interface AdminUserListResponse {
  items: AdminUserListItem[]
  total: number
}

export interface AdminRecentActivity {
  event_type: string
  created_at: string
}

export interface AdminRecentFeedback {
  id: string
  title: string
  status: string
  created_at: string
}

export interface AdminUserDetail {
  id: string
  email: string
  display_name: string
  signature: string | null
  is_active: boolean
  is_admin: boolean
  created_at: string
  last_login_at: string | null
  last_seen_at: string | null
  login_count: number
  password_changed_at: string | null
  cloud_project_count: number
  cloud_backup_count: number
  total_storage_bytes: number
  feedback_count: number
  recent_activity: AdminRecentActivity[]
  recent_feedback: AdminRecentFeedback[]
}

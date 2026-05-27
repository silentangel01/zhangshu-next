export interface CloudAccountStatus {
  logged_in: boolean
  cloud_available: boolean
  email: string | null
  display_name: string | null
}

export interface CloudAuthToken {
  access_token: string
  refresh_token: string
  expires_in: number
}

export interface CloudProjectStatus {
  cloud_enabled: boolean
  cloud_project_id: string | null
  provider: string
  last_backup_at: string | null
  last_restore_at: string | null
  status: string
  last_error: string | null
}

export interface CloudBackupRecord {
  id: string
  project_id: string
  cloud_backup_id: string | null
  filename: string
  size_bytes: number | null
  checksum_sha256: string | null
  encryption_mode: string
  status: string
  error_message: string | null
  created_at: string
  uploaded_at: string | null
}

export interface CloudBackupListResponse {
  items: CloudBackupRecord[]
  total: number
}

export interface CloudRestoreReport {
  project_id: string
  project_title: string
  counts: {
    volumes: number
    chapters: number
    materials: number
  }
  warnings: string[]
  errors: string[]
}

// ── Network diagnostics ──────────────────────────────────────────

export type CloudNetworkMode = 'auto' | 'secure_direct' | 'system_proxy' | 'compat_no_sni'

export interface CloudNetworkSettings {
  mode: CloudNetworkMode
  last_working_mode: CloudNetworkMode | null
  base_url_configured: boolean
}

export interface CloudNetworkDiagnosticStep {
  name: string
  ok: boolean
  latency_ms: number | null
  error_kind: string
  message: string
  suggestion: string
}

export interface CloudNetworkDiagnosticReport {
  ok: boolean
  recommended_mode: CloudNetworkMode
  summary: string
  steps: CloudNetworkDiagnosticStep[]
}

// ── Account & privacy ────────────────────────────────────────────────

export interface CloudAccountProfile {
  id: string
  email: string
  display_name: string
  signature: string | null
  avatar_url: string | null
  avatar_updated_at: string | null
  password_changed_at: string | null
  created_at: string
}

export interface CloudSession {
  id: string
  user_agent: string | null
  client_ip: string | null
  last_used_at: string | null
  created_at: string
  revoked: boolean
}

export interface CloudSessionList {
  sessions: CloudSession[]
  total: number
}

export interface CloudChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface CloudUpdateProfileRequest {
  display_name?: string
  signature?: string
}

export interface CloudAvatarResponse {
  avatar_url: string
  avatar_updated_at: string
}

// ── Usage ────────────────────────────────────────────────────────────

export interface CloudUsage {
  storage_used_bytes: number
  storage_quota_bytes: number
  backup_count: number
  backup_count_quota: number
  backup_init_used_last_hour: number
  backup_init_limit_per_hour: number
  max_backup_size_bytes: number
}

// ── Export & deletion ────────────────────────────────────────────────

export interface CloudAccountExport {
  account: {
    id: string
    email: string
    display_name: string
    created_at: string
  }
  projects: Array<{
    id: string
    title: string
    created_at: string
  }>
  backups: Array<{
    id: string
    project_id: string
    filename: string
    size_bytes: number | null
    checksum_sha256: string | null
    status: string
    created_at: string
    uploaded_at: string | null
  }>
  usage: CloudUsage
  exported_at: string
}

export interface CloudDeletionRequest {
  request_id: string
  expires_at: string
  project_count: number
  backup_count: number
  total_size_bytes: number
  confirmation_text: string
}

export interface CloudDeletionConfirmRequest {
  request_id: string
  confirmation_text: string
}

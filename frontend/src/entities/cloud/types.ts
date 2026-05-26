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

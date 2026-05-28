export interface AuditLogEntry {
  id: string
  event: string
  request_id: string
  client_ip: string
  user_id: string
  project_id: string
  backup_id: string
  result: string
  reason_code: string
  extra_json: string | null
  created_at: string | null
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
}

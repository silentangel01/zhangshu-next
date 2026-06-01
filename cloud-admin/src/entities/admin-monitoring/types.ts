export interface BillingInfo {
  available_amount: string
  currency: string
  credit_amount: string
  mybank_credit_amount: string
  available_cash_amount: string
}

export interface OSSBucketStats {
  storage_bytes: number
  object_count: number
  standard_storage: number
  ia_storage: number
  archive_storage: number
  bucket_name: string
}

export interface ServerInfo {
  name: string
  status: string
  public_ip: string
  spec: string
  os_name: string
  created_at: string
  expired_at: string
  region_id: string
  charge_type: string
}

export interface ServerMonitor {
  cpu_usage: number
  memory_usage: number
  disk_read_iops: number
  disk_write_iops: number
  net_rx_bps: number
  net_tx_bps: number
  timestamp: string
  available: boolean
}

export interface ServerStatus {
  info: ServerInfo
  monitor: ServerMonitor
}

export interface ModuleResponse<T> {
  data: T | null
  error: string | null
  cached_at: string
  ttl_seconds: number
}

export interface MonitoringOverview {
  billing: ModuleResponse<BillingInfo>
  oss: ModuleResponse<OSSBucketStats>
  server: ModuleResponse<ServerStatus>
}

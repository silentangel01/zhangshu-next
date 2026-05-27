import { apiRequest } from '@/shared/api/client'
import type { MonitoringOverview } from './types'

export function getMonitoringOverview() {
  return apiRequest<MonitoringOverview>('/api/admin/monitoring/overview')
}

export function refreshMonitoring(module?: string) {
  const q = module ? `?module=${encodeURIComponent(module)}` : ''
  return apiRequest<MonitoringOverview>(`/api/admin/monitoring/refresh${q}`)
}

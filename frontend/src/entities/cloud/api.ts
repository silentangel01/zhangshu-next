import { apiRequest } from '@/shared/api/client'

import type {
  CloudAccountStatus,
  CloudBackupListResponse,
  CloudBackupRecord,
  CloudNetworkDiagnosticReport,
  CloudNetworkMode,
  CloudNetworkSettings,
  CloudProjectStatus,
  CloudRestoreReport,
} from './types'

export function getCloudAccountStatus(): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/account/status')
}

export function cloudLogin(email: string, password: string): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/login', {
    method: 'POST',
    body: { email, password },
  })
}

export function cloudRegister(
  email: string,
  password: string,
  displayName: string,
): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/register', {
    method: 'POST',
    body: { email, password, display_name: displayName },
  })
}

export function cloudLogout(): Promise<void> {
  return apiRequest<void>('/api/cloud/auth/logout', { method: 'POST' })
}

export function enableCloud(
  projectId: string,
  cloudProjectId?: string,
): Promise<CloudProjectStatus> {
  return apiRequest<CloudProjectStatus>(`/api/projects/${projectId}/cloud/enable`, {
    method: 'POST',
    body: cloudProjectId ? { cloud_project_id: cloudProjectId } : {},
  })
}

export function getCloudStatus(projectId: string): Promise<CloudProjectStatus> {
  return apiRequest<CloudProjectStatus>(`/api/projects/${projectId}/cloud/status`)
}

export function triggerCloudBackup(projectId: string): Promise<CloudBackupRecord> {
  return apiRequest<CloudBackupRecord>(`/api/projects/${projectId}/cloud/backups`, {
    method: 'POST',
  })
}

export function listCloudBackups(projectId: string): Promise<CloudBackupListResponse> {
  return apiRequest<CloudBackupListResponse>(`/api/projects/${projectId}/cloud/backups`)
}

export function restoreCloudBackup(
  projectId: string,
  recordId: string,
): Promise<CloudRestoreReport> {
  return apiRequest<CloudRestoreReport>(
    `/api/projects/${projectId}/cloud/backups/${recordId}/restore`,
    { method: 'POST' },
  )
}

// ── Network diagnostics ──────────────────────────────────────────

export function getCloudNetworkSettings(): Promise<CloudNetworkSettings> {
  return apiRequest<CloudNetworkSettings>('/api/cloud/network/settings')
}

export function setCloudNetworkSettings(mode: CloudNetworkMode): Promise<CloudNetworkSettings> {
  return apiRequest<CloudNetworkSettings>('/api/cloud/network/settings', {
    method: 'PUT',
    body: { mode },
  })
}

export function runCloudNetworkDiagnostics(): Promise<CloudNetworkDiagnosticReport> {
  return apiRequest<CloudNetworkDiagnosticReport>('/api/cloud/network/diagnose', {
    method: 'POST',
    body: {},
  })
}

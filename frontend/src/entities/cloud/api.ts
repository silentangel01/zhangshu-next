import { apiRequest, apiUpload } from '@/shared/api/client'

import type {
  CloudAccountExport,
  CloudAccountProfile,
  CloudAccountStatus,
  CloudAvatarResponse,
  CloudBackupListResponse,
  CloudBackupRecord,
  CloudDeletionConfirmRequest,
  CloudDeletionRequest,
  CloudNetworkDiagnosticReport,
  CloudNetworkMode,
  CloudNetworkSettings,
  CloudProjectImportResult,
  CloudProjectStatus,
  CloudRemoteProject,
  CloudRestoreReport,
  CloudSessionList,
  CloudSyncConflict,
  CloudSyncRunResult,
  CloudSyncSnapshot,
  CloudSyncStatus,
  CloudUsage,
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

export function refreshCloudToken(): Promise<{ refreshed: boolean }> {
  return apiRequest<{ refreshed: boolean }>('/api/cloud/auth/refresh', {
    method: 'POST',
  })
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

// ── Account & privacy ────────────────────────────────────────────────

export function getCloudAccountProfile(): Promise<CloudAccountProfile> {
  return apiRequest<CloudAccountProfile>('/api/cloud/account/profile')
}

export function updateCloudAccountProfile(params: {
  display_name?: string
  signature?: string
}): Promise<CloudAccountProfile> {
  return apiRequest<CloudAccountProfile>('/api/cloud/account/profile', {
    method: 'PATCH',
    body: params,
  })
}

export function uploadCloudAvatar(file: File): Promise<CloudAvatarResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return apiUpload<CloudAvatarResponse>('/api/cloud/account/avatar', formData)
}

export function deleteCloudAvatar(): Promise<void> {
  return apiRequest<void>('/api/cloud/account/avatar', { method: 'DELETE' })
}

export function changeCloudPassword(oldPassword: string, newPassword: string): Promise<void> {
  return apiRequest<void>('/api/cloud/account/password/change', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  })
}

export function revokeAllCloudSessions(): Promise<{ revoked_count: number }> {
  return apiRequest<{ revoked_count: number }>('/api/cloud/account/sessions/revoke-all', {
    method: 'POST',
  })
}

export function getCloudUsage(): Promise<CloudUsage> {
  return apiRequest<CloudUsage>('/api/cloud/account/usage')
}

export function exportCloudAccountData(): Promise<CloudAccountExport> {
  return apiRequest<CloudAccountExport>('/api/cloud/account/export')
}

export function requestCloudAccountDeletion(password: string): Promise<CloudDeletionRequest> {
  return apiRequest<CloudDeletionRequest>('/api/cloud/account/delete-request', {
    method: 'POST',
    body: { password },
  })
}

export function confirmCloudAccountDeletion(
  requestId: string,
  confirmationText: string,
): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>('/api/cloud/account', {
    method: 'DELETE',
    body: { request_id: requestId, confirmation_text: confirmationText },
  })
}

// ── Incremental sync ──────────────────────────────────────────────

export function getCloudSyncStatus(projectId: string): Promise<CloudSyncStatus> {
  return apiRequest<CloudSyncStatus>(`/api/projects/${projectId}/cloud/sync/status`)
}

export function runCloudSync(projectId: string): Promise<CloudSyncRunResult> {
  return apiRequest<CloudSyncRunResult>(`/api/projects/${projectId}/cloud/sync/run`, {
    method: 'POST',
    body: {},
  })
}

export function pullCloudSync(projectId: string): Promise<CloudSyncRunResult> {
  return apiRequest<CloudSyncRunResult>(`/api/projects/${projectId}/cloud/sync/pull`, {
    method: 'POST',
  })
}

export function listCloudSyncSnapshots(
  projectId: string,
  params: { entity_type: string; entity_id: string },
): Promise<CloudSyncSnapshot[]> {
  const query = `?entity_type=${encodeURIComponent(params.entity_type)}&entity_id=${encodeURIComponent(params.entity_id)}`
  return apiRequest<CloudSyncSnapshot[]>(
    `/api/projects/${projectId}/cloud/sync/snapshots${query}`,
  )
}

export function listCloudSyncConflicts(
  projectId: string,
  resolved = false,
): Promise<CloudSyncConflict[]> {
  return apiRequest<CloudSyncConflict[]>(
    `/api/projects/${projectId}/cloud/sync/conflicts?resolved=${resolved}`,
  )
}

export async function listRemoteCloudProjects(): Promise<CloudRemoteProject[]> {
  const result = await apiRequest<CloudRemoteProject[] | { items: CloudRemoteProject[] }>(
    '/api/cloud/projects',
  )
  if (Array.isArray(result)) return result
  return result.items ?? []
}

export function importRemoteCloudProject(
  cloudProjectId: string,
): Promise<CloudProjectImportResult> {
  return apiRequest<CloudProjectImportResult>(
    `/api/cloud/projects/${cloudProjectId}/import`,
    { method: 'POST' },
  )
}

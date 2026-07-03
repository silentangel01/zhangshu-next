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
  CloudEmailCheckResponse,
  CloudEmailCodePurpose,
  CloudPhoneCheckResponse,
  CloudPhoneCodePurpose,
  CloudNetworkDiagnosticReport,
  CloudNetworkMode,
  CloudNetworkSettings,
  CloudOAuthPollResponse,
  CloudOAuthProvider,
  CloudOAuthStartResponse,
  CloudProjectImportResult,
  CloudProjectStatus,
  CloudRemoteProject,
  CloudRestoreReport,
  CloudSendEmailCodeResponse,
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

export function cloudLoginWithEmailCode(
  email: string,
  verificationCode: string,
): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/login/email-code', {
    method: 'POST',
    body: { email, verification_code: verificationCode },
  })
}

export function cloudLoginWithPhoneCode(
  phoneNumber: string,
  verificationCode: string,
): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/login/phone-code', {
    method: 'POST',
    body: { phone_number: phoneNumber, verification_code: verificationCode },
  })
}

export function checkCloudEmail(email: string): Promise<CloudEmailCheckResponse> {
  return apiRequest<CloudEmailCheckResponse>('/api/cloud/auth/email/check', {
    method: 'POST',
    body: { email },
  })
}

export function checkCloudPhone(phoneNumber: string): Promise<CloudPhoneCheckResponse> {
  return apiRequest<CloudPhoneCheckResponse>('/api/cloud/auth/phone/check', {
    method: 'POST',
    body: { phone_number: phoneNumber },
  })
}

export function sendCloudEmailCode(
  email: string,
  purpose: CloudEmailCodePurpose,
): Promise<CloudSendEmailCodeResponse> {
  return apiRequest<CloudSendEmailCodeResponse>('/api/cloud/auth/email-code/send', {
    method: 'POST',
    body: { email, purpose },
  })
}

export function sendCloudPhoneCode(
  phoneNumber: string,
  purpose: CloudPhoneCodePurpose,
): Promise<CloudSendEmailCodeResponse> {
  return apiRequest<CloudSendEmailCodeResponse>('/api/cloud/auth/phone-code/send', {
    method: 'POST',
    body: { phone_number: phoneNumber, purpose },
  })
}

export function cloudRegister(
  email: string,
  password: string,
  displayName: string,
  verificationCode: string,
): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/register', {
    method: 'POST',
    body: { email, password, display_name: displayName, verification_code: verificationCode },
  })
}

export function cloudRegisterWithPhone(
  phoneNumber: string,
  verificationCode: string,
  displayName: string,
): Promise<CloudAccountStatus> {
  return apiRequest<CloudAccountStatus>('/api/cloud/auth/register/phone', {
    method: 'POST',
    body: { phone_number: phoneNumber, verification_code: verificationCode, display_name: displayName },
  })
}

export function startCloudOAuthLogin(
  provider: CloudOAuthProvider,
): Promise<CloudOAuthStartResponse> {
  return apiRequest<CloudOAuthStartResponse>(`/api/cloud/auth/oauth/${provider}/start`, {
    method: 'POST',
    body: {},
  })
}

export function pollCloudOAuthLogin(
  sessionId: string,
  pollToken: string,
): Promise<CloudOAuthPollResponse> {
  return apiRequest<CloudOAuthPollResponse>(
    `/api/cloud/auth/oauth/session/${encodeURIComponent(sessionId)}?poll_token=${encodeURIComponent(pollToken)}`,
  )
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

export function sendCloudBindEmailCode(email: string): Promise<CloudSendEmailCodeResponse> {
  return apiRequest<CloudSendEmailCodeResponse>('/api/cloud/account/bind/email-code/send', {
    method: 'POST',
    body: { email },
  })
}

export function sendCloudBindPhoneCode(phoneNumber: string): Promise<CloudSendEmailCodeResponse> {
  return apiRequest<CloudSendEmailCodeResponse>('/api/cloud/account/bind/phone-code/send', {
    method: 'POST',
    body: { phone_number: phoneNumber },
  })
}

export function bindCloudEmail(
  email: string,
  verificationCode: string,
): Promise<CloudAccountProfile> {
  return apiRequest<CloudAccountProfile>('/api/cloud/account/bind/email', {
    method: 'POST',
    body: { email, verification_code: verificationCode },
  })
}

export function bindCloudPhone(
  phoneNumber: string,
  verificationCode: string,
): Promise<CloudAccountProfile> {
  return apiRequest<CloudAccountProfile>('/api/cloud/account/bind/phone', {
    method: 'POST',
    body: { phone_number: phoneNumber, verification_code: verificationCode },
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

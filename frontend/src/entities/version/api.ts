import { apiRequest } from '@/shared/api/client'

import type {
  CleanupVersionsResponse,
  CreateVersionSnapshotRequest,
  RestoreVersionResponse,
  UpdateVersionRequest,
  VersionCompareRequest,
  VersionCompareResponse,
  VersionDetail,
  VersionListItem,
  VersionListResponse,
  VersionSnapshotTargetsResponse,
  VersionSummaryResponse,
} from './types'

export function listVersions(
  projectId: string,
  params?: {
    entity_type?: string
    entity_id?: string
    source?: string
    pinned?: boolean
    keyword?: string
    limit?: number
    offset?: number
  },
): Promise<VersionListResponse> {
  const qs = new URLSearchParams()
  if (params?.entity_type) qs.set('entity_type', params.entity_type)
  if (params?.entity_id) qs.set('entity_id', params.entity_id)
  if (params?.source) qs.set('source', params.source)
  if (params?.pinned != null) qs.set('pinned', String(params.pinned))
  if (params?.keyword) qs.set('keyword', params.keyword)
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  return apiRequest<VersionListResponse>(
    `/api/projects/${projectId}/versions?${qs.toString()}`,
  )
}

export function getVersion(
  projectId: string,
  versionRef: string,
): Promise<VersionDetail> {
  return apiRequest<VersionDetail>(
    `/api/projects/${projectId}/versions/${versionRef}`,
  )
}

export function createSnapshot(
  projectId: string,
  data: CreateVersionSnapshotRequest,
): Promise<VersionListItem> {
  return apiRequest<VersionListItem>(
    `/api/projects/${projectId}/versions/snapshots`,
    {
      method: 'POST',
      body: data,
    },
  )
}

export function updateVersion(
  projectId: string,
  versionRef: string,
  data: UpdateVersionRequest,
): Promise<VersionListItem> {
  return apiRequest<VersionListItem>(
    `/api/projects/${projectId}/versions/${versionRef}`,
    {
      method: 'PATCH',
      body: data,
    },
  )
}

export function deleteVersion(
  projectId: string,
  versionRef: string,
): Promise<void> {
  return apiRequest<void>(
    `/api/projects/${projectId}/versions/${versionRef}`,
    { method: 'DELETE' },
  )
}

export function compareVersions(
  projectId: string,
  data: VersionCompareRequest,
): Promise<VersionCompareResponse> {
  return apiRequest<VersionCompareResponse>(
    `/api/projects/${projectId}/versions/compare`,
    {
      method: 'POST',
      body: data,
    },
  )
}

export function restoreVersion(
  projectId: string,
  versionRef: string,
): Promise<RestoreVersionResponse> {
  return apiRequest<RestoreVersionResponse>(
    `/api/projects/${projectId}/versions/${versionRef}/restore`,
    { method: 'POST' },
  )
}

export function cleanupVersions(
  projectId: string,
  keepDays?: number,
  source?: string,
): Promise<CleanupVersionsResponse> {
  const qs = new URLSearchParams()
  if (keepDays != null) qs.set('keep_days', String(keepDays))
  if (source) qs.set('source', source)
  return apiRequest<CleanupVersionsResponse>(
    `/api/projects/${projectId}/versions/cleanup?${qs.toString()}`,
    { method: 'POST' },
  )
}

export function getVersionSummary(
  projectId: string,
): Promise<VersionSummaryResponse> {
  return apiRequest<VersionSummaryResponse>(
    `/api/projects/${projectId}/versions/summary`,
  )
}

export function listVersionSnapshotTargets(
  projectId: string,
  params?: {
    entity_type?: string
    keyword?: string
    limit?: number
  },
): Promise<VersionSnapshotTargetsResponse> {
  const qs = new URLSearchParams()
  if (params?.entity_type) qs.set('entity_type', params.entity_type)
  if (params?.keyword) qs.set('keyword', params.keyword)
  if (params?.limit != null) qs.set('limit', String(params.limit))
  return apiRequest<VersionSnapshotTargetsResponse>(
    `/api/projects/${projectId}/versions/snapshot-targets?${qs.toString()}`,
  )
}

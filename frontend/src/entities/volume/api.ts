import { apiRequest } from '@/shared/api/client'

import type { CreateVolumePayload, UpdateVolumePayload, Volume } from './types'

export function listVolumes(projectId: string): Promise<Volume[]> {
  return apiRequest<Volume[]>(`/api/projects/${projectId}/volumes`)
}

export function createVolume(projectId: string, payload: CreateVolumePayload): Promise<Volume> {
  return apiRequest<Volume>(`/api/projects/${projectId}/volumes`, {
    method: 'POST',
    body: payload,
  })
}

export function updateVolume(volumeId: string, payload: UpdateVolumePayload): Promise<Volume> {
  return apiRequest<Volume>(`/api/volumes/${volumeId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteVolume(volumeId: string): Promise<Volume | void> {
  return apiRequest<Volume | void>(`/api/volumes/${volumeId}`, {
    method: 'DELETE',
  })
}

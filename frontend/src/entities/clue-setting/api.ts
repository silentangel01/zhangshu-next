import { apiRequest } from '@/shared/api/client'

import type { AddClueSettingPayload, ClueSettingLink, UpdateClueSettingPayload } from './types'

export function listClueSettings(clueId: string): Promise<ClueSettingLink[]> {
  return apiRequest<ClueSettingLink[]>(`/api/clues/${clueId}/settings`)
}

export function addClueSetting(clueId: string, payload: AddClueSettingPayload): Promise<ClueSettingLink> {
  return apiRequest<ClueSettingLink>(`/api/clues/${clueId}/settings`, {
    method: 'POST',
    body: payload,
  })
}

export function updateClueSetting(linkId: string, payload: UpdateClueSettingPayload): Promise<ClueSettingLink> {
  return apiRequest<ClueSettingLink>(`/api/clue-settings/${linkId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteClueSetting(linkId: string): Promise<void> {
  return apiRequest<void>(`/api/clue-settings/${linkId}`, {
    method: 'DELETE',
  })
}

import { apiRequest } from '@/shared/api/client'

import type { AddClueCharacterPayload, ClueCharacterLink, UpdateClueCharacterPayload } from './types'

export function listClueCharacters(clueId: string): Promise<ClueCharacterLink[]> {
  return apiRequest<ClueCharacterLink[]>(`/api/clues/${clueId}/characters`)
}

export function addClueCharacter(clueId: string, payload: AddClueCharacterPayload): Promise<ClueCharacterLink> {
  return apiRequest<ClueCharacterLink>(`/api/clues/${clueId}/characters`, {
    method: 'POST',
    body: payload,
  })
}

export function updateClueCharacter(linkId: string, payload: UpdateClueCharacterPayload): Promise<ClueCharacterLink> {
  return apiRequest<ClueCharacterLink>(`/api/clue-characters/${linkId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteClueCharacter(linkId: string): Promise<void> {
  return apiRequest<void>(`/api/clue-characters/${linkId}`, {
    method: 'DELETE',
  })
}

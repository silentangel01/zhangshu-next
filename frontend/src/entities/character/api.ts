import { apiRequest } from '@/shared/api/client'

import type {
  Character,
  CharacterFilters,
  CreateCharacterPayload,
  UpdateCharacterPayload,
} from './types'

function buildQuery(filters?: CharacterFilters): string {
  if (!filters) {
    return ''
  }

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      params.set(key, value)
    }
  }

  const query = params.toString()
  return query ? `?${query}` : ''
}

export function listProjectCharacters(
  projectId: string,
  filters?: CharacterFilters,
): Promise<Character[]> {
  return apiRequest<Character[]>(`/api/projects/${projectId}/characters${buildQuery(filters)}`)
}

export function createCharacter(
  projectId: string,
  payload: CreateCharacterPayload,
): Promise<Character> {
  return apiRequest<Character>(`/api/projects/${projectId}/characters`, {
    method: 'POST',
    body: payload,
  })
}

export function getCharacter(characterId: string): Promise<Character> {
  return apiRequest<Character>(`/api/characters/${characterId}`)
}

export function updateCharacter(
  characterId: string,
  payload: UpdateCharacterPayload,
): Promise<Character> {
  return apiRequest<Character>(`/api/characters/${characterId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteCharacter(characterId: string): Promise<Character | void> {
  return apiRequest<Character | void>(`/api/characters/${characterId}`, {
    method: 'DELETE',
  })
}

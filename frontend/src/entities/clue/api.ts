import { apiRequest } from '@/shared/api/client'

import type { Clue, ClueFilters, CreateCluePayload, UpdateCluePayload } from './types'

export function listProjectClues(projectId: string, filters: ClueFilters = {}): Promise<Clue[]> {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value)
    }
  })
  const query = params.toString()
  return apiRequest<Clue[]>(`/api/projects/${projectId}/clues${query ? `?${query}` : ''}`)
}

export function createClue(projectId: string, payload: CreateCluePayload): Promise<Clue> {
  return apiRequest<Clue>(`/api/projects/${projectId}/clues`, {
    method: 'POST',
    body: payload,
  })
}

export function getClue(clueId: string): Promise<Clue> {
  return apiRequest<Clue>(`/api/clues/${clueId}`)
}

export function updateClue(clueId: string, payload: UpdateCluePayload): Promise<Clue> {
  return apiRequest<Clue>(`/api/clues/${clueId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteClue(clueId: string): Promise<Clue> {
  return apiRequest<Clue>(`/api/clues/${clueId}`, {
    method: 'DELETE',
  })
}

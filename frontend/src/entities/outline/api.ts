import { apiRequest } from '@/shared/api/client'

import type {
  OutlineFilters,
  OutlineItem,
  OutlineItemCreatePayload,
  OutlineItemUpdatePayload,
} from './types'

function buildQuery(filters?: OutlineFilters): string {
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

export function listProjectOutlines(
  projectId: string,
  filters?: OutlineFilters,
): Promise<OutlineItem[]> {
  return apiRequest<OutlineItem[]>(`/api/projects/${projectId}/outlines${buildQuery(filters)}`)
}

export function createOutline(
  projectId: string,
  payload: OutlineItemCreatePayload,
): Promise<OutlineItem> {
  return apiRequest<OutlineItem>(`/api/projects/${projectId}/outlines`, {
    method: 'POST',
    body: payload,
  })
}

export function getOutline(outlineId: string): Promise<OutlineItem> {
  return apiRequest<OutlineItem>(`/api/outlines/${outlineId}`)
}

export function updateOutline(
  outlineId: string,
  payload: OutlineItemUpdatePayload,
): Promise<OutlineItem> {
  return apiRequest<OutlineItem>(`/api/outlines/${outlineId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteOutline(outlineId: string): Promise<OutlineItem | void> {
  return apiRequest<OutlineItem | void>(`/api/outlines/${outlineId}`, {
    method: 'DELETE',
  })
}

export function listChapterOutlines(chapterId: string): Promise<OutlineItem[]> {
  return apiRequest<OutlineItem[]>(`/api/chapters/${chapterId}/outlines`)
}

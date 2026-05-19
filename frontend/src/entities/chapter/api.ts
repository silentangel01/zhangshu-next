import { apiRequest } from '@/shared/api/client'

import type { Chapter, CreateChapterPayload, UpdateChapterPayload } from './types'

export function listChapters(projectId: string): Promise<Chapter[]> {
  return apiRequest<Chapter[]>(`/api/projects/${projectId}/chapters`)
}

export function createChapter(projectId: string, payload: CreateChapterPayload): Promise<Chapter> {
  return apiRequest<Chapter>(`/api/projects/${projectId}/chapters`, {
    method: 'POST',
    body: payload,
  })
}

export function getChapter(chapterId: string): Promise<Chapter> {
  return apiRequest<Chapter>(`/api/chapters/${chapterId}`)
}

export function updateChapter(chapterId: string, payload: UpdateChapterPayload): Promise<Chapter> {
  return apiRequest<Chapter>(`/api/chapters/${chapterId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteChapter(chapterId: string): Promise<Chapter | void> {
  return apiRequest<Chapter | void>(`/api/chapters/${chapterId}`, {
    method: 'DELETE',
  })
}

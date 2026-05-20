import { apiRequest } from '@/shared/api/client'

import type { AddChapterCluePayload, ChapterClueLink, UpdateChapterCluePayload } from './types'

export function listChapterClues(chapterId: string): Promise<ChapterClueLink[]> {
  return apiRequest<ChapterClueLink[]>(`/api/chapters/${chapterId}/clues`)
}

export function addChapterClue(chapterId: string, payload: AddChapterCluePayload): Promise<ChapterClueLink> {
  return apiRequest<ChapterClueLink>(`/api/chapters/${chapterId}/clues`, {
    method: 'POST',
    body: payload,
  })
}

export function updateChapterClue(linkId: string, payload: UpdateChapterCluePayload): Promise<ChapterClueLink> {
  return apiRequest<ChapterClueLink>(`/api/chapter-clues/${linkId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteChapterClue(linkId: string): Promise<void> {
  return apiRequest<void>(`/api/chapter-clues/${linkId}`, {
    method: 'DELETE',
  })
}

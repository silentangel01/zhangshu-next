import { apiRequest } from '@/shared/api/client'

import type {
  AddChapterCharacterPayload,
  ChapterCharacterLink,
  UpdateChapterCharacterPayload,
} from './types'

export function listChapterCharacters(chapterId: string): Promise<ChapterCharacterLink[]> {
  return apiRequest<ChapterCharacterLink[]>(`/api/chapters/${chapterId}/characters`)
}

export function addChapterCharacter(
  chapterId: string,
  payload: AddChapterCharacterPayload,
): Promise<ChapterCharacterLink> {
  return apiRequest<ChapterCharacterLink>(`/api/chapters/${chapterId}/characters`, {
    method: 'POST',
    body: payload,
  })
}

export function updateChapterCharacter(
  linkId: string,
  payload: UpdateChapterCharacterPayload,
): Promise<ChapterCharacterLink> {
  return apiRequest<ChapterCharacterLink>(`/api/chapter-characters/${linkId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteChapterCharacter(linkId: string): Promise<void> {
  return apiRequest<void>(`/api/chapter-characters/${linkId}`, {
    method: 'DELETE',
  })
}

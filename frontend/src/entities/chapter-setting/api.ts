import { apiRequest } from '@/shared/api/client'

import type {
  AddChapterSettingPayload,
  ChapterSettingLink,
  UpdateChapterSettingPayload,
} from './types'

export function listChapterSettings(chapterId: string): Promise<ChapterSettingLink[]> {
  return apiRequest<ChapterSettingLink[]>(`/api/chapters/${chapterId}/settings`)
}

export function addChapterSetting(
  chapterId: string,
  payload: AddChapterSettingPayload,
): Promise<ChapterSettingLink> {
  return apiRequest<ChapterSettingLink>(`/api/chapters/${chapterId}/settings`, {
    method: 'POST',
    body: payload,
  })
}

export function updateChapterSetting(
  linkId: string,
  payload: UpdateChapterSettingPayload,
): Promise<ChapterSettingLink> {
  return apiRequest<ChapterSettingLink>(`/api/chapter-settings/${linkId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteChapterSetting(linkId: string): Promise<void> {
  return apiRequest<void>(`/api/chapter-settings/${linkId}`, {
    method: 'DELETE',
  })
}

import type { Chapter } from '@/entities/chapter/types'
import { apiRequest } from '@/shared/api/client'

import type {
  ChapterVersionDetail,
  ChapterVersionListItem,
  CreateChapterVersionPayload,
} from './types'

export function listChapterVersions(chapterId: string): Promise<ChapterVersionListItem[]> {
  return apiRequest<ChapterVersionListItem[]>(`/api/chapters/${chapterId}/versions`)
}

export function getChapterVersion(versionId: string): Promise<ChapterVersionDetail> {
  return apiRequest<ChapterVersionDetail>(`/api/chapter-versions/${versionId}`)
}

export function createChapterVersion(
  chapterId: string,
  payload: CreateChapterVersionPayload,
): Promise<ChapterVersionDetail> {
  return apiRequest<ChapterVersionDetail>(`/api/chapters/${chapterId}/versions`, {
    method: 'POST',
    body: payload,
  })
}

export function restoreChapterVersion(chapterId: string, versionId: string): Promise<Chapter> {
  return apiRequest<Chapter>(`/api/chapters/${chapterId}/restore-version/${versionId}`, {
    method: 'POST',
  })
}

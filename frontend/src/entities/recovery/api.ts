import { apiRequest } from '@/shared/api/client'

import type { Chapter } from '@/entities/chapter/types'
import type { RecoveryDraft, RecoveryDraftPayload } from './types'

export function listRecoveryDrafts(chapterId: string): Promise<RecoveryDraft[]> {
  return apiRequest<RecoveryDraft[]>(`/api/chapters/${chapterId}/recovery-drafts`)
}

export function createRecoveryDraft(
  chapterId: string,
  payload: RecoveryDraftPayload,
): Promise<RecoveryDraft> {
  return apiRequest<RecoveryDraft>(`/api/chapters/${chapterId}/recovery-drafts`, {
    method: 'POST',
    body: payload,
  })
}

export function recoverDraft(draftId: string): Promise<Chapter> {
  return apiRequest<Chapter>(`/api/recovery-drafts/${draftId}/recover`, {
    method: 'PATCH',
  })
}

export function deleteRecoveryDraft(draftId: string): Promise<void> {
  return apiRequest<void>(`/api/recovery-drafts/${draftId}`, {
    method: 'DELETE',
  })
}

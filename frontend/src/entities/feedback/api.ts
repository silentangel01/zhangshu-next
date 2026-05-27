import { apiRequest, apiUpload } from '@/shared/api/client'

import type {
  FeedbackHistoryListResponse,
  FeedbackReplyListResponse,
  FeedbackSubmitResponse,
} from './types'

export function submitFeedback(formData: FormData): Promise<FeedbackSubmitResponse> {
  return apiUpload<FeedbackSubmitResponse>('/api/cloud/feedback', formData)
}

export function listFeedbackReplies(
  feedbackId: string
): Promise<FeedbackReplyListResponse> {
  return apiRequest<FeedbackReplyListResponse>(
    `/api/cloud/feedback/${feedbackId}/replies`
  )
}

export function listFeedbackHistory(
  limit = 50,
  offset = 0
): Promise<FeedbackHistoryListResponse> {
  return apiRequest<FeedbackHistoryListResponse>(
    `/api/cloud/feedback?limit=${limit}&offset=${offset}`
  )
}

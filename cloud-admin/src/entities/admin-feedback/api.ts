import { apiRequest } from '@/shared/api/client'
import type {
  CreateReplyRequest,
  FeedbackAttachment,
  FeedbackListResponse,
  FeedbackReply,
  FeedbackReplyListResponse,
  FeedbackTicket,
  UpdateFeedbackRequest,
} from './types'

export function listFeedback(params?: {
  status?: string
  category?: string
  priority?: string
  keyword?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.category) search.set('category', params.category)
  if (params?.priority) search.set('priority', params.priority)
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  const q = search.toString()
  return apiRequest<FeedbackListResponse>(`/api/admin/feedback${q ? `?${q}` : ''}`)
}

export function getFeedback(id: string) {
  return apiRequest<FeedbackTicket>(`/api/admin/feedback/${id}`)
}

export function updateFeedback(id: string, body: UpdateFeedbackRequest) {
  return apiRequest<FeedbackTicket>(`/api/admin/feedback/${id}`, {
    method: 'PATCH',
    body,
  })
}

export function listAttachments(feedbackId: string) {
  return apiRequest<FeedbackAttachment[]>(
    `/api/admin/feedback/${feedbackId}/attachments`
  )
}

export function getAttachmentDownloadUrl(feedbackId: string, attachmentId: string) {
  return apiRequest<{ download_url: string }>(
    `/api/admin/feedback/${feedbackId}/attachments/${attachmentId}/download-url`
  )
}

export function listReplies(feedbackId: string) {
  return apiRequest<FeedbackReplyListResponse>(
    `/api/admin/feedback/${feedbackId}/replies`
  )
}

export function createReply(feedbackId: string, body: CreateReplyRequest) {
  return apiRequest<FeedbackReply>(`/api/admin/feedback/${feedbackId}/replies`, {
    method: 'POST',
    body,
  })
}

export function deleteReply(feedbackId: string, replyId: string) {
  return apiRequest<void>(`/api/admin/feedback/${feedbackId}/replies/${replyId}`, {
    method: 'DELETE',
  })
}

export type FeedbackCategory = 'bug' | 'suggestion' | 'data_loss' | 'cloud' | 'ui' | 'other'

export interface FeedbackSubmitResponse {
  id: string
  status: string
  uploaded_attachments: number
  failed_attachments: number
}

export interface FeedbackReply {
  id: string
  ticket_id: string
  author_type: string
  author_display_name: string | null
  content: string
  created_at: string
}

export interface FeedbackReplyListResponse {
  items: FeedbackReply[]
  total: number
}

export interface FeedbackHistoryItem {
  id: string
  category: string
  title: string
  description: string
  status: string
  priority: string | null
  attachment_count: number
  reply_count: number
  created_at: string
  updated_at: string
}

export interface FeedbackHistoryListResponse {
  items: FeedbackHistoryItem[]
  total: number
}

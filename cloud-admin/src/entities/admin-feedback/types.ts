export interface FeedbackTicket {
  id: string
  user_id: string | null
  contact_email: string | null
  category: string
  title: string
  description: string
  status: string
  priority: string | null
  app_version: string | null
  platform: string | null
  network_mode: string | null
  client_diagnostics_json: string | null
  attachment_count: number
  total_size_bytes: number
  admin_note: string | null
  reply_count?: number
  created_at: string
  updated_at: string
}

export interface FeedbackAttachment {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  status: string
  created_at: string
}

export interface FeedbackListResponse {
  items: FeedbackTicket[]
  total: number
}

export interface UpdateFeedbackRequest {
  status?: string
  priority?: string
  admin_note?: string
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

export interface CreateReplyRequest {
  content: string
}

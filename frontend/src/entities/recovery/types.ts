export interface RecoveryDraft {
  id: string
  project_id: string
  chapter_id: string
  content: string
  saved_content_snapshot: string
  word_count: number
  created_at: string
  updated_at: string
}

export interface RecoveryDraftPayload {
  content: string
  saved_content_snapshot: string
}

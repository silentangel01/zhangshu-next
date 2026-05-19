export type ChapterStatus = 'draft' | 'writing' | 'revised' | 'completed'

export interface Chapter {
  id: string
  project_id: string
  volume_id: string | null
  title: string
  content: string
  order_index: number
  status: ChapterStatus
  word_count: number
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface CreateChapterPayload {
  title: string
  volume_id?: string | null
  content: string
  order_index: number
  status: ChapterStatus
}

export interface UpdateChapterPayload {
  title?: string
  volume_id?: string | null
  content?: string
  order_index?: number
  status?: ChapterStatus
}

export interface UpdateChapterMetadataPayload {
  title: string
  volume_id: string | null
  order_index: number
  status: ChapterStatus
}

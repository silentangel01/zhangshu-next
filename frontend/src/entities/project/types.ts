export type ProjectStatus = 'planning' | 'writing' | 'paused' | 'completed' | 'archived'

export interface Project {
  id: string
  title: string
  author: string | null
  genre: string | null
  summary: string | null
  tags: string[]
  cover_image_path: string | null
  status: ProjectStatus
  target_word_count: number | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface CreateProjectPayload {
  title: string
  author?: string | null
  genre?: string | null
  summary?: string | null
  tags?: string[]
  status?: ProjectStatus
  target_word_count?: number | null
}

export interface UpdateProjectPayload {
  title?: string
  author?: string | null
  genre?: string | null
  summary?: string | null
  tags?: string[]
  status?: ProjectStatus
  target_word_count?: number | null
}

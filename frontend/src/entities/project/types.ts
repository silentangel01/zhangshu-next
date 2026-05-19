export interface Project {
  id: string
  title: string
  genre: string | null
  summary: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface CreateProjectPayload {
  title: string
  genre?: string | null
  summary?: string | null
}

export interface UpdateProjectPayload {
  title?: string
  genre?: string | null
  summary?: string | null
}

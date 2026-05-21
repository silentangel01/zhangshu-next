export type ReviewScope = 'chapter' | 'volume' | 'project'

export interface ProhibitedTerm {
  id: string
  term: string
  severity: string
  suggestion: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface ProhibitedTermPayload {
  term: string
  severity: string
  suggestion: string
  enabled: boolean
}

export interface ProhibitedTermUpdatePayload {
  term?: string
  severity?: string
  suggestion?: string
  enabled?: boolean
}

export interface ReviewCheckPayload {
  scope: ReviewScope
  chapter_id?: string | null
  volume_id?: string | null
}

export interface CheckResult {
  id: string
  project_id: string
  chapter_id: string
  chapter_title: string | null
  volume_title: string | null
  rule_type: string
  matched_text: string
  severity: string
  position_start: number
  position_end: number
  suggestion: string
  created_at: string
}

export interface ReviewCheckResponse {
  total: number
  results: CheckResult[]
}

export type ClueStatus = 'planned' | 'planted' | 'developing' | 'resolved' | 'abandoned'
export type ClueVisibility = 'hidden' | 'hinted' | 'revealed'
export type ClueImportance = 'low' | 'normal' | 'high' | 'critical'

export interface Clue {
  id: string
  project_id: string
  title: string
  description: string
  setup_chapter_id: string | null
  payoff_chapter_id: string | null
  status: ClueStatus
  visibility: ClueVisibility
  importance: ClueImportance
  payoff_plan: string
  actual_payoff: string
  note: string
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface ClueFilters {
  status?: ClueStatus
  visibility?: ClueVisibility
  importance?: ClueImportance
  keyword?: string
}

export interface CreateCluePayload {
  title: string
  description?: string
  setup_chapter_id?: string | null
  payoff_chapter_id?: string | null
  status?: ClueStatus
  visibility?: ClueVisibility
  importance?: ClueImportance
  payoff_plan?: string
  actual_payoff?: string
  note?: string
}

export type UpdateCluePayload = Partial<CreateCluePayload>

export const clueStatusLabels: Record<ClueStatus, string> = {
  planned: '计划中',
  planted: '已埋设',
  developing: '推进中',
  resolved: '已回收',
  abandoned: '已废弃',
}

export const clueVisibilityLabels: Record<ClueVisibility, string> = {
  hidden: '隐藏',
  hinted: '暗示',
  revealed: '已揭示',
}

export const clueImportanceLabels: Record<ClueImportance, string> = {
  low: '低',
  normal: '普通',
  high: '重要',
  critical: '核心',
}

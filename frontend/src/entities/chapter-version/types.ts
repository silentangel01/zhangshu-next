export type ChapterVersionSource =
  | 'manual'
  | 'milestone'
  | 'manual_save'
  | 'autosave'
  | 'restore'
  | 'before_restore'

export interface ChapterVersionListItem {
  id: string
  chapter_id: string
  project_id: string
  title: string
  word_count: number
  source: ChapterVersionSource
  note: string | null
  label: string | null
  is_pinned: boolean
  created_at: string
}

export interface ChapterVersionDetail extends ChapterVersionListItem {
  content: string
}

export interface CreateChapterVersionPayload {
  source?: ChapterVersionSource
  note?: string | null
}

export const CHAPTER_VERSION_SOURCE_LABELS: Record<string, string> = {
  milestone: '里程碑',
  manual_save: '手动保存',
  autosave: '自动快照',
  before_restore: '恢复前备份',
  restore: '恢复记录',
  manual: '旧手动版本',
}

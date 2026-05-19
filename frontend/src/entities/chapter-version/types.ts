export type ChapterVersionSource = 'manual' | 'autosave' | 'restore' | 'before_restore'

export interface ChapterVersionListItem {
  id: string
  chapter_id: string
  project_id: string
  title: string
  word_count: number
  source: ChapterVersionSource
  note: string | null
  created_at: string
}

export interface ChapterVersionDetail extends ChapterVersionListItem {
  content: string
}

export interface CreateChapterVersionPayload {
  source: ChapterVersionSource
  note?: string | null
}

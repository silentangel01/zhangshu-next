import type { Clue } from '@/entities/clue/types'

export type ChapterClueRelationType = 'setup' | 'mention' | 'develop' | 'payoff' | 'related'

export interface ChapterClueLink {
  id: string
  project_id: string
  chapter_id: string
  clue_id: string
  relation_type: ChapterClueRelationType
  note: string
  created_at: string
  updated_at: string
  clue: Clue
}

export interface AddChapterCluePayload {
  clue_id: string
  relation_type: ChapterClueRelationType
  note?: string
}

export interface UpdateChapterCluePayload {
  relation_type?: ChapterClueRelationType
  note?: string
}

export const chapterClueRelationLabels: Record<ChapterClueRelationType, string> = {
  setup: '埋设',
  mention: '提及',
  develop: '推进',
  payoff: '回收',
  related: '相关',
}

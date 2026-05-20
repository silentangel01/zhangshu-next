import type { Character } from '@/entities/character/types'

export type ChapterCharacterRelationType =
  | 'appears'
  | 'mentioned'
  | 'pov'
  | 'conflict'
  | 'supports'

export interface ChapterCharacterLink {
  id: string
  project_id: string
  chapter_id: string
  character_id: string
  relation_type: ChapterCharacterRelationType
  note: string
  created_at: string
  updated_at: string
  character: Character
}

export interface AddChapterCharacterPayload {
  character_id: string
  relation_type: ChapterCharacterRelationType
  note?: string
}

export interface UpdateChapterCharacterPayload {
  relation_type?: ChapterCharacterRelationType
  note?: string
}

export const chapterCharacterRelationLabels: Record<ChapterCharacterRelationType, string> = {
  appears: '出场',
  mentioned: '被提及',
  pov: '视角人物',
  conflict: '发生冲突',
  supports: '协助推动剧情',
}

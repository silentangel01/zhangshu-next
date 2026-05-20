import type { SettingItem } from '@/entities/setting/types'

export type ChapterSettingRelationType =
  | 'referenced'
  | 'appears'
  | 'explained'
  | 'changed'
  | 'conflict_check'

export interface ChapterSettingLink {
  id: string
  project_id: string
  chapter_id: string
  setting_item_id: string
  relation_type: ChapterSettingRelationType
  note: string
  created_at: string
  updated_at: string
  setting_item: SettingItem
}

export interface AddChapterSettingPayload {
  setting_item_id: string
  relation_type: ChapterSettingRelationType
  note?: string
}

export interface UpdateChapterSettingPayload {
  relation_type?: ChapterSettingRelationType
  note?: string
}

export const chapterSettingRelationLabels: Record<ChapterSettingRelationType, string> = {
  referenced: '相关设定',
  appears: '本章出现',
  explained: '本章解释',
  changed: '本章变更',
  conflict_check: '需要检查一致性',
}

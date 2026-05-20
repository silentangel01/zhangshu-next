import type { SettingItem } from '@/entities/setting/types'

export type ClueSettingRelationType = 'related' | 'depends_on' | 'explains' | 'conflicts_with'

export interface ClueSettingLink {
  id: string
  project_id: string
  clue_id: string
  setting_item_id: string
  relation_type: ClueSettingRelationType
  note: string
  created_at: string
  updated_at: string
  setting: SettingItem
}

export interface AddClueSettingPayload {
  setting_item_id: string
  relation_type: ClueSettingRelationType
  note?: string
}

export interface UpdateClueSettingPayload {
  relation_type?: ClueSettingRelationType
  note?: string
}

export const clueSettingRelationLabels: Record<ClueSettingRelationType, string> = {
  related: '相关',
  depends_on: '依赖设定',
  explains: '解释伏笔',
  conflicts_with: '存在冲突',
}

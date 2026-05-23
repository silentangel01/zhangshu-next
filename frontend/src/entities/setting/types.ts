export type SettingNodeKind = 'folder' | 'page'

export type SettingItemType =
  | 'world'
  | 'location'
  | 'organization'
  | 'power_system'
  | 'history'
  | 'technology'
  | 'rule'
  | 'race'
  | 'object'
  | 'character'
  | 'custom'

export type SettingCanonStatus = 'draft' | 'confirmed' | 'deprecated' | 'conflicted'
export type SettingImportance = 'low' | 'normal' | 'high' | 'critical'

export interface SettingItem {
  id: string
  project_id: string
  parent_id: string | null
  title: string
  item_type: SettingItemType
  canon_status: SettingCanonStatus
  summary: string
  detail: string
  tags: string
  order_index: number
  importance: SettingImportance
  node_kind: SettingNodeKind
  folder_key: string | null
  folder_default_item_type: SettingItemType | null
  is_system: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface SettingPayload {
  parent_id?: string | null
  title: string
  item_type?: SettingItemType
  canon_status?: SettingCanonStatus
  summary?: string
  detail?: string
  tags?: string
  order_index?: number
  importance?: SettingImportance
  node_kind?: SettingNodeKind
  folder_default_item_type?: SettingItemType | null
}

export type CreateSettingPayload = SettingPayload
export type UpdateSettingPayload = Partial<SettingPayload>

export interface SettingFilters {
  item_type?: SettingItemType
  canon_status?: SettingCanonStatus
  importance?: SettingImportance
  keyword?: string
  node_kind?: SettingNodeKind
}

export const settingItemTypeLabels: Record<SettingItemType, string> = {
  world: '世界观',
  location: '地点',
  organization: '组织 / 势力',
  power_system: '力量体系',
  history: '历史',
  technology: '科技 / 技术',
  rule: '规则',
  race: '种族',
  object: '物品',
  character: '人物',
  custom: '自定义',
}

export const settingCanonStatusLabels: Record<SettingCanonStatus, string> = {
  draft: '草稿',
  confirmed: '已确认',
  deprecated: '已废弃',
  conflicted: '存在冲突',
}

export const settingImportanceLabels: Record<SettingImportance, string> = {
  low: '低',
  normal: '普通',
  high: '重要',
  critical: '核心',
}

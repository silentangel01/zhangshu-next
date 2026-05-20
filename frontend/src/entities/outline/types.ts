export type OutlineItemType =
  | 'book_outline'
  | 'volume_outline'
  | 'chapter_outline'
  | 'scene'
  | 'plot_point'
  | 'note'

export type OutlineStatus = 'planned' | 'writing' | 'done' | 'abandoned'
export type OutlineImportance = 'normal' | 'important' | 'critical'

export interface OutlineItem {
  id: string
  project_id: string
  parent_id: string | null
  volume_id: string | null
  chapter_id: string | null
  title: string
  content: string
  item_type: OutlineItemType
  status: OutlineStatus
  order_index: number
  importance: OutlineImportance
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface OutlineItemCreatePayload {
  parent_id?: string | null
  volume_id?: string | null
  chapter_id?: string | null
  title: string
  content?: string
  item_type: OutlineItemType
  status?: OutlineStatus
  order_index?: number
  importance?: OutlineImportance
}

export interface OutlineItemUpdatePayload {
  parent_id?: string | null
  volume_id?: string | null
  chapter_id?: string | null
  title?: string
  content?: string
  item_type?: OutlineItemType
  status?: OutlineStatus
  order_index?: number
  importance?: OutlineImportance
}

export interface OutlineFilters {
  volume_id?: string
  chapter_id?: string
  item_type?: OutlineItemType
  status?: OutlineStatus
}

export interface OutlineTreeNodeData {
  item: OutlineItem
  children: OutlineTreeNodeData[]
}

export const outlineItemTypeLabels: Record<OutlineItemType, string> = {
  book_outline: '全书大纲',
  volume_outline: '分卷大纲',
  chapter_outline: '章节细纲',
  scene: '场景',
  plot_point: '剧情节点',
  note: '备注',
}

export const outlineStatusLabels: Record<OutlineStatus, string> = {
  planned: '计划中',
  writing: '写作中',
  done: '已完成',
  abandoned: '已废弃',
}

export const outlineImportanceLabels: Record<OutlineImportance, string> = {
  normal: '普通',
  important: '重要',
  critical: '关键',
}

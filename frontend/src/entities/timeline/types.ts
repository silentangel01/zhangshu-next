import type { Chapter } from '@/entities/chapter/types'
import type { SettingItem } from '@/entities/setting/types'

export type TimelineEventType =
  | 'plot'
  | 'background'
  | 'character'
  | 'world'
  | 'clue'
  | 'conflict'
  | 'custom'

export type TimelineEventImportance = 'low' | 'normal' | 'high' | 'critical'
export type TimelineEventStatus = 'planned' | 'happened' | 'revised' | 'deprecated'

export interface TimelineEvent {
  id: string
  project_id: string
  title: string
  description: string
  event_type: TimelineEventType
  story_date: string | null
  story_time: string | null
  order_index: number
  importance: TimelineEventImportance
  status: TimelineEventStatus
  chapter_id: string | null
  location_setting_id: string | null
  note: string
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
  chapter: Chapter | null
  location_setting: SettingItem | null
}

export interface TimelineFilters {
  event_type?: TimelineEventType
  status?: TimelineEventStatus
  importance?: TimelineEventImportance
  chapter_id?: string
  keyword?: string
}

export interface CreateTimelineEventPayload {
  title: string
  description?: string
  event_type?: TimelineEventType
  story_date?: string | null
  story_time?: string | null
  order_index?: number
  importance?: TimelineEventImportance
  status?: TimelineEventStatus
  chapter_id?: string | null
  location_setting_id?: string | null
  note?: string
}

export type UpdateTimelineEventPayload = Partial<CreateTimelineEventPayload>

export const timelineEventTypeLabels: Record<TimelineEventType, string> = {
  plot: '剧情事件',
  background: '背景事件',
  character: '人物事件',
  world: '世界事件',
  clue: '伏笔事件',
  conflict: '冲突事件',
  custom: '自定义',
}

export const timelineEventImportanceLabels: Record<TimelineEventImportance, string> = {
  low: '低',
  normal: '普通',
  high: '重要',
  critical: '核心',
}

export const timelineEventStatusLabels: Record<TimelineEventStatus, string> = {
  planned: '计划中',
  happened: '已发生',
  revised: '已调整',
  deprecated: '已废弃',
}

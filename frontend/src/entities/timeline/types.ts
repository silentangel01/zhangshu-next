import type { Chapter } from '@/entities/chapter/types'
import type { SettingItem } from '@/entities/setting/types'

export type TimelineEventType = 'plot' | 'background' | 'character' | 'world' | 'clue' | 'conflict' | 'custom'
export type TimelineEventImportance = 'low' | 'normal' | 'high' | 'critical'
export type TimelineEventStatus = 'planned' | 'happened' | 'revised' | 'deprecated'

export type TimelineTrackType = 'main' | 'character' | 'organization' | 'setting' | 'clue' | 'volume' | 'custom'
export type TimelineEdgeType = 'cause' | 'parallel' | 'clue_payoff' | 'conflict' | 'echo' | 'related' | 'custom'
export type TimelineEdgeLineStyle = 'straight' | 'arc' | 'dashed' | 'arrow'
export type TimelineEdgeVisibility = 'normal' | 'subtle' | 'hidden'

export interface TimelineTrack {
  id: string
  project_id: string
  title: string
  description: string
  track_type: TimelineTrackType
  bound_type: string | null
  bound_id: string | null
  order_index: number
  color: string | null
  is_main: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface TimelineTrackCreatePayload {
  title: string
  description?: string
  track_type?: TimelineTrackType
  bound_type?: string | null
  bound_id?: string | null
  order_index?: number
  color?: string | null
  is_main?: boolean
}

export type TimelineTrackUpdatePayload = Partial<TimelineTrackCreatePayload>

export interface TimelineEdge {
  id: string
  project_id: string
  from_event_id: string
  to_event_id: string
  edge_type: TimelineEdgeType
  line_style: TimelineEdgeLineStyle
  label: string
  note: string
  visibility: TimelineEdgeVisibility
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface TimelineEdgeCreatePayload {
  from_event_id: string
  to_event_id: string
  edge_type?: TimelineEdgeType
  line_style?: TimelineEdgeLineStyle
  label?: string
  note?: string
  visibility?: TimelineEdgeVisibility
}

export type TimelineEdgeUpdatePayload = Partial<TimelineEdgeCreatePayload>

export interface TimelineEvent {
  id: string
  project_id: string
  title: string
  description: string
  event_type: TimelineEventType
  story_date: string | null
  story_time: string | null
  order_index: number
  position_index: number
  importance: TimelineEventImportance
  status: TimelineEventStatus
  chapter_id: string | null
  location_setting_id: string | null
  track_id: string | null
  note: string
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
  chapter: Chapter | null
  location_setting: SettingItem | null
}

export interface TimelineEventCreatePayload {
  title: string
  description?: string
  event_type?: TimelineEventType
  story_date?: string | null
  story_time?: string | null
  order_index?: number
  position_index?: number
  importance?: TimelineEventImportance
  status?: TimelineEventStatus
  chapter_id?: string | null
  location_setting_id?: string | null
  track_id?: string | null
  note?: string
}

export type TimelineEventUpdatePayload = Partial<TimelineEventCreatePayload>

export interface TimelineEventFilters {
  event_type?: TimelineEventType
  status?: TimelineEventStatus
  importance?: TimelineEventImportance
  chapter_id?: string
  keyword?: string
}

export interface TimelineEdgeFilters {
  edge_type?: TimelineEdgeType
  visibility?: TimelineEdgeVisibility
}

export type TimelineFilters = TimelineEventFilters
export type CreateTimelineEventPayload = TimelineEventCreatePayload
export type UpdateTimelineEventPayload = TimelineEventUpdatePayload
export type CreateTimelineTrackPayload = TimelineTrackCreatePayload
export type UpdateTimelineTrackPayload = TimelineTrackUpdatePayload
export type CreateTimelineEdgePayload = TimelineEdgeCreatePayload
export type UpdateTimelineEdgePayload = TimelineEdgeUpdatePayload

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

export const timelineTrackTypeLabels: Record<TimelineTrackType, string> = {
  main: '主时间轴',
  character: '角色时间轴',
  organization: '组织时间轴',
  setting: '设定时间轴',
  clue: '伏笔时间轴',
  volume: '分卷时间轴',
  custom: '自定义时间轴',
}

export const timelineEdgeTypeLabels: Record<TimelineEdgeType, string> = {
  cause: '因果',
  parallel: '并行',
  clue_payoff: '伏笔回收',
  conflict: '冲突',
  echo: '呼应',
  related: '相关',
  custom: '自定义',
}

export const timelineEdgeLineStyleLabels: Record<TimelineEdgeLineStyle, string> = {
  straight: '直线',
  arc: '弧线',
  dashed: '虚线',
  arrow: '箭头线',
}

export const timelineEdgeVisibilityLabels: Record<TimelineEdgeVisibility, string> = {
  normal: '正常',
  subtle: '弱化',
  hidden: '隐藏',
}

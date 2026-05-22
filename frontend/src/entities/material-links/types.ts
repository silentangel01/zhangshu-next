export type TimelineEventCharacterRelationType =
  | 'appears'
  | 'pov'
  | 'conflict'
  | 'supports'
  | 'mentions'
  | 'causes'
  | 'affected_by'
  | 'related'

export type TimelineEventSettingRelationType =
  | 'location'
  | 'object'
  | 'organization'
  | 'rule'
  | 'background'
  | 'affected_by'
  | 'related'

export type TimelineEventClueRelationType =
  | 'setup'
  | 'develop'
  | 'payoff'
  | 'reveals'
  | 'causes'
  | 'related'

export type OutlineCharacterRelationType =
  | 'appears'
  | 'pov'
  | 'conflict'
  | 'supports'
  | 'target'
  | 'related'

export type OutlineSettingRelationType =
  | 'location'
  | 'object'
  | 'organization'
  | 'rule'
  | 'background'
  | 'related'

export type OutlineClueRelationType = 'setup' | 'develop' | 'payoff' | 'hint' | 'related'

export type OutlineTimelineEventRelationType =
  | 'planned_event'
  | 'actual_event'
  | 'previous'
  | 'next'
  | 'parallel'
  | 'related'

export type MaterialLinkTargetType =
  | 'chapter'
  | 'outline'
  | 'character'
  | 'setting'
  | 'clue'
  | 'timeline_event'
  | 'graph_node'

export type MaterialLinkRelation = {
  id?: string
  project_id: string
  source_type: MaterialLinkTargetType
  source_id: string
  target_type: MaterialLinkTargetType
  target_id: string
  relation_type: string
  note?: string
  created_at?: string
  updated_at?: string
}

export type MaterialLinkPayload = {
  relation_type?: string
  note?: string
}

export type BaseMaterialLink = {
  id: string
  project_id: string
  relation_type: string
  note: string
  created_at: string
  updated_at: string
}

export type TimelineEventCharacterLink = BaseMaterialLink & {
  timeline_event_id: string
  character_id: string
}

export type TimelineEventSettingLink = BaseMaterialLink & {
  timeline_event_id: string
  setting_id: string
}

export type TimelineEventClueLink = BaseMaterialLink & {
  timeline_event_id: string
  clue_id: string
}

export type OutlineCharacterLink = BaseMaterialLink & {
  outline_item_id: string
  character_id: string
}

export type OutlineSettingLink = BaseMaterialLink & {
  outline_item_id: string
  setting_id: string
}

export type OutlineClueLink = BaseMaterialLink & {
  outline_item_id: string
  clue_id: string
}

export type OutlineTimelineEventLink = BaseMaterialLink & {
  outline_item_id: string
  timeline_event_id: string
}

export type TimelineEventCharacterLinkPayload = {
  character_id: string
  relation_type?: TimelineEventCharacterRelationType
  note?: string
}

export type TimelineEventSettingLinkPayload = {
  setting_id: string
  relation_type?: TimelineEventSettingRelationType
  note?: string
}

export type TimelineEventClueLinkPayload = {
  clue_id: string
  relation_type?: TimelineEventClueRelationType
  note?: string
}

export type OutlineCharacterLinkPayload = {
  character_id: string
  relation_type?: OutlineCharacterRelationType
  note?: string
}

export type OutlineSettingLinkPayload = {
  setting_id: string
  relation_type?: OutlineSettingRelationType
  note?: string
}

export type OutlineClueLinkPayload = {
  clue_id: string
  relation_type?: OutlineClueRelationType
  note?: string
}

export type OutlineTimelineEventLinkPayload = {
  timeline_event_id: string
  relation_type?: OutlineTimelineEventRelationType
  note?: string
}

export type MaterialLinkSummary = {
  timeline_event_character_count: number
  timeline_event_setting_count: number
  timeline_event_clue_count: number
  outline_character_count: number
  outline_setting_count: number
  outline_clue_count: number
  outline_timeline_event_count: number
}

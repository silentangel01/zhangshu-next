export type CreativeReminderSeverity = 'info' | 'warning' | 'critical'
export type CreativeReminderType =
  | 'important_clue_unresolved'
  | 'important_character_absent'
  | 'outline_not_done_for_written_chapter'
  | 'timeline_event_missing_chapter'
  | 'graph_node_broken_binding'
  | 'clue_payoff_without_setup'
  | 'setting_used_but_draft'

export type CreativeReminderTargetType =
  | 'clue'
  | 'character'
  | 'outline'
  | 'timeline_event'
  | 'graph_node'
  | 'setting'
  | 'chapter'

export interface CreativeReminder {
  id: string
  project_id: string
  chapter_id: string | null
  type: CreativeReminderType
  severity: CreativeReminderSeverity
  title: string
  message: string
  reason: string
  suggestion: string
  scope_label: string
  context_summary: string | null
  target_type: CreativeReminderTargetType
  target_id: string
  action_label: string
  created_from: 'rule'
}

export interface CreativeReminderList {
  total: number
  items: CreativeReminder[]
}

export interface CreativeReminderFilters {
  scope?: 'project' | 'chapter'
  chapter_id?: string
  severity?: CreativeReminderSeverity
  reminder_type?: CreativeReminderType
}

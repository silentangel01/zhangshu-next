export type VersionEntityType =
  | 'chapter'
  | 'setting'
  | 'character'
  | 'clue'
  | 'outline'
  | 'knowledge_source'

export type VersionSource = 'manual' | 'autosave' | 'restore' | 'before_restore'

export interface VersionListItem {
  version_ref: string
  entity_type: string
  entity_id: string
  entity_title: string
  source: string
  label: string | null
  note: string | null
  is_pinned: boolean
  word_count: number
  created_at: string
}

export interface VersionListResponse {
  project_id: string
  total: number
  limit: number
  offset: number
  versions: VersionListItem[]
}

export interface VersionDetail extends VersionListItem {
  content_text: string
  snapshot_json: Record<string, unknown> | null
  metadata: Record<string, unknown> | null
}

export interface CreateVersionSnapshotRequest {
  entity_type: VersionEntityType
  entity_id: string
  label?: string | null
  note?: string | null
}

export interface UpdateVersionRequest {
  label?: string | null
  note?: string | null
  is_pinned?: boolean
}

export interface VersionCompareRequest {
  version_ref_a: string
  version_ref_b?: string | null
}

export interface DiffLine {
  tag: 'equal' | 'insert' | 'delete' | 'replace'
  old_text: string
  new_text: string
}

export interface VersionCompareResponse {
  version_ref_a: string
  version_ref_b: string | null
  title_a: string
  title_b: string
  diff: DiffLine[]
}

export interface RestoreVersionResponse {
  version_ref: string
  entity_type: string
  entity_id: string
  before_restore_ref: string
  message: string
}

export interface CleanupVersionsResponse {
  deleted_count: number
  message: string
}

export const VERSION_ENTITY_TYPE_LABELS: Record<string, string> = {
  chapter: '正文',
  setting: '设定',
  character: '人物',
  clue: '伏笔',
  outline: '大纲',
  knowledge_source: '知识库',
}

export const VERSION_SOURCE_LABELS: Record<string, string> = {
  manual: '手动快照',
  autosave: '自动保存',
  restore: '恢复记录',
  before_restore: '恢复前备份',
}

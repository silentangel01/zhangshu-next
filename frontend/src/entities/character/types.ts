export type CharacterRole =
  | 'protagonist'
  | 'deuteragonist'
  | 'antagonist'
  | 'supporting'
  | 'minor'
  | 'unknown'

export type CharacterImportance = 'low' | 'normal' | 'high' | 'critical'
export type CharacterStatus = 'active' | 'inactive' | 'dead' | 'missing' | 'unknown'

export interface CharacterProfileSection {
  id: string
  title: string
  content: string
  order: number
  collapsed: boolean
}

export interface CharacterProfileDimension {
  id: string
  name: string
  value: number
  max: number
  order: number
}

export interface Character {
  id: string
  project_id: string
  name: string
  role: CharacterRole
  importance: CharacterImportance
  status: CharacterStatus
  faction: string | null
  summary: string
  biography: string
  appearance: string
  personality: string
  background: string
  ability: string
  motivation: string
  secret: string
  arc: string
  notes: string
  profile_sections: CharacterProfileSection[]
  profile_dimensions: CharacterProfileDimension[]
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface CharacterPayload {
  name: string
  role: CharacterRole
  importance: CharacterImportance
  status: CharacterStatus
  faction?: string | null
  summary?: string
  biography?: string
  appearance?: string
  personality?: string
  background?: string
  ability?: string
  motivation?: string
  secret?: string
  arc?: string
  notes?: string
  profile_sections?: CharacterProfileSection[]
  profile_dimensions?: CharacterProfileDimension[]
}

export type CreateCharacterPayload = CharacterPayload
export type UpdateCharacterPayload = Partial<CharacterPayload>

export interface CharacterFilters {
  role?: CharacterRole
  importance?: CharacterImportance
  status?: CharacterStatus
  keyword?: string
}

export const characterRoleLabels: Record<CharacterRole, string> = {
  protagonist: '主角',
  deuteragonist: '重要配角',
  antagonist: '反派',
  supporting: '配角',
  minor: '次要人物',
  unknown: '未分类',
}

export const characterImportanceLabels: Record<CharacterImportance, string> = {
  low: '低',
  normal: '普通',
  high: '重要',
  critical: '核心',
}

export const characterStatusLabels: Record<CharacterStatus, string> = {
  active: '活跃',
  inactive: '暂未出场',
  dead: '死亡',
  missing: '失踪',
  unknown: '未知',
}

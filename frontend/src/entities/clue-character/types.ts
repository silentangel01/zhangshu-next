import type { Character } from '@/entities/character/types'

export type ClueCharacterRelationType = 'related' | 'holder' | 'discoverer' | 'target' | 'blocker'

export interface ClueCharacterLink {
  id: string
  project_id: string
  clue_id: string
  character_id: string
  relation_type: ClueCharacterRelationType
  note: string
  created_at: string
  updated_at: string
  character: Character
}

export interface AddClueCharacterPayload {
  character_id: string
  relation_type: ClueCharacterRelationType
  note?: string
}

export interface UpdateClueCharacterPayload {
  relation_type?: ClueCharacterRelationType
  note?: string
}

export const clueCharacterRelationLabels: Record<ClueCharacterRelationType, string> = {
  related: '相关',
  holder: '持有者',
  discoverer: '发现者',
  target: '关联对象',
  blocker: '阻碍者',
}

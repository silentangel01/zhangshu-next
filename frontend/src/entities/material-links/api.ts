import { addChapterCharacter, deleteChapterCharacter, listChapterCharacters } from '@/entities/chapter-character/api'
import { addChapterClue, deleteChapterClue, listChapterClues } from '@/entities/chapter-clue/api'
import { addChapterSetting, deleteChapterSetting, listChapterSettings } from '@/entities/chapter-setting/api'
import { addClueCharacter, deleteClueCharacter, listClueCharacters } from '@/entities/clue-character/api'
import { addClueSetting, deleteClueSetting, listClueSettings } from '@/entities/clue-setting/api'
import { apiRequest } from '@/shared/api/client'

import type {
  MaterialLinkPayload,
  MaterialLinkRelation,
  MaterialLinkSummary,
  MaterialLinkTargetType,
  OutlineCharacterLink,
  OutlineCharacterLinkPayload,
  OutlineClueLink,
  OutlineClueLinkPayload,
  OutlineSettingLink,
  OutlineSettingLinkPayload,
  OutlineTimelineEventLink,
  OutlineTimelineEventLinkPayload,
  TimelineEventCharacterLink,
  TimelineEventCharacterLinkPayload,
  TimelineEventClueLink,
  TimelineEventClueLinkPayload,
  TimelineEventSettingLink,
  TimelineEventSettingLinkPayload,
} from './types'

type LinkApiSpec = {
  list: (sourceId: string) => Promise<unknown[]>
  add: (sourceId: string, payload: Record<string, unknown>) => Promise<unknown>
  remove: (sourceId: string, targetId: string, linkId?: string) => Promise<void>
  targetKey: string
  normalize: (item: Record<string, unknown>, sourceId: string) => MaterialLinkRelation
}

function createNormalizer(
  sourceType: MaterialLinkTargetType,
  targetType: MaterialLinkTargetType,
  sourceKey: string,
  targetKey: string,
) {
  return (item: Record<string, unknown>, sourceId: string): MaterialLinkRelation => ({
    id: typeof item.id === 'string' ? item.id : undefined,
    project_id: String(item.project_id ?? ''),
    source_type: sourceType,
    source_id: String(item[sourceKey] ?? sourceId),
    target_type: targetType,
    target_id: String(item[targetKey] ?? ''),
    relation_type: String(item.relation_type ?? 'related'),
    note: typeof item.note === 'string' ? item.note : '',
    created_at: typeof item.created_at === 'string' ? item.created_at : undefined,
    updated_at: typeof item.updated_at === 'string' ? item.updated_at : undefined,
  })
}

const linkApiRegistry: Partial<Record<MaterialLinkTargetType, Partial<Record<MaterialLinkTargetType, LinkApiSpec>>>> = {
  chapter: {
    character: {
      list: (sourceId) => listChapterCharacters(sourceId),
      add: (sourceId, payload) =>
        addChapterCharacter(sourceId, {
          character_id: String(payload.character_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'appears',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: async (_sourceId, _targetId, linkId) => {
        if (!linkId) throw new Error('移除章节人物关联需要关联 ID。')
        await deleteChapterCharacter(linkId)
      },
      targetKey: 'character_id',
      normalize: createNormalizer('chapter', 'character', 'chapter_id', 'character_id'),
    },
    setting: {
      list: (sourceId) => listChapterSettings(sourceId),
      add: (sourceId, payload) =>
        addChapterSetting(sourceId, {
          setting_item_id: String(payload.setting_item_id ?? payload.setting_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'referenced',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: async (_sourceId, _targetId, linkId) => {
        if (!linkId) throw new Error('移除章节设定关联需要关联 ID。')
        await deleteChapterSetting(linkId)
      },
      targetKey: 'setting_item_id',
      normalize: createNormalizer('chapter', 'setting', 'chapter_id', 'setting_item_id'),
    },
    clue: {
      list: (sourceId) => listChapterClues(sourceId),
      add: (sourceId, payload) =>
        addChapterClue(sourceId, {
          clue_id: String(payload.clue_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: async (_sourceId, _targetId, linkId) => {
        if (!linkId) throw new Error('移除章节伏笔关联需要关联 ID。')
        await deleteChapterClue(linkId)
      },
      targetKey: 'clue_id',
      normalize: createNormalizer('chapter', 'clue', 'chapter_id', 'clue_id'),
    },
  },
  outline: {
    character: {
      list: (sourceId) => listOutlineCharacters(sourceId),
      add: (sourceId, payload) =>
        addOutlineCharacter(sourceId, {
          character_id: String(payload.character_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeOutlineCharacter(sourceId, targetId),
      targetKey: 'character_id',
      normalize: createNormalizer('outline', 'character', 'outline_item_id', 'character_id'),
    },
    setting: {
      list: (sourceId) => listOutlineSettings(sourceId),
      add: (sourceId, payload) =>
        addOutlineSetting(sourceId, {
          setting_id: String(payload.setting_id ?? payload.setting_item_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeOutlineSetting(sourceId, targetId),
      targetKey: 'setting_id',
      normalize: createNormalizer('outline', 'setting', 'outline_item_id', 'setting_id'),
    },
    clue: {
      list: (sourceId) => listOutlineClues(sourceId),
      add: (sourceId, payload) =>
        addOutlineClue(sourceId, {
          clue_id: String(payload.clue_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeOutlineClue(sourceId, targetId),
      targetKey: 'clue_id',
      normalize: createNormalizer('outline', 'clue', 'outline_item_id', 'clue_id'),
    },
    timeline_event: {
      list: (sourceId) => listOutlineTimelineEvents(sourceId),
      add: (sourceId, payload) =>
        addOutlineTimelineEvent(sourceId, {
          timeline_event_id: String(payload.timeline_event_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeOutlineTimelineEvent(sourceId, targetId),
      targetKey: 'timeline_event_id',
      normalize: createNormalizer('outline', 'timeline_event', 'outline_item_id', 'timeline_event_id'),
    },
  },
  clue: {
    character: {
      list: (sourceId) => listClueCharacters(sourceId),
      add: (sourceId, payload) =>
        addClueCharacter(sourceId, {
          character_id: String(payload.character_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: async (_sourceId, _targetId, linkId) => {
        if (!linkId) throw new Error('移除伏笔人物关联需要关联 ID。')
        await deleteClueCharacter(linkId)
      },
      targetKey: 'character_id',
      normalize: createNormalizer('clue', 'character', 'clue_id', 'character_id'),
    },
    setting: {
      list: (sourceId) => listClueSettings(sourceId),
      add: (sourceId, payload) =>
        addClueSetting(sourceId, {
          setting_item_id: String(payload.setting_item_id ?? payload.setting_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: async (_sourceId, _targetId, linkId) => {
        if (!linkId) throw new Error('移除伏笔设定关联需要关联 ID。')
        await deleteClueSetting(linkId)
      },
      targetKey: 'setting_item_id',
      normalize: createNormalizer('clue', 'setting', 'clue_id', 'setting_item_id'),
    },
  },
  timeline_event: {
    character: {
      list: (sourceId) => listTimelineEventCharacters(sourceId),
      add: (sourceId, payload) =>
        addTimelineEventCharacter(sourceId, {
          character_id: String(payload.character_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeTimelineEventCharacter(sourceId, targetId),
      targetKey: 'character_id',
      normalize: createNormalizer('timeline_event', 'character', 'timeline_event_id', 'character_id'),
    },
    setting: {
      list: (sourceId) => listTimelineEventSettings(sourceId),
      add: (sourceId, payload) =>
        addTimelineEventSetting(sourceId, {
          setting_id: String(payload.setting_id ?? payload.setting_item_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeTimelineEventSetting(sourceId, targetId),
      targetKey: 'setting_id',
      normalize: createNormalizer('timeline_event', 'setting', 'timeline_event_id', 'setting_id'),
    },
    clue: {
      list: (sourceId) => listTimelineEventClues(sourceId),
      add: (sourceId, payload) =>
        addTimelineEventClue(sourceId, {
          clue_id: String(payload.clue_id ?? ''),
          relation_type: (payload.relation_type as never) ?? 'related',
          note: typeof payload.note === 'string' ? payload.note : '',
        }),
      remove: (sourceId, targetId) => removeTimelineEventClue(sourceId, targetId),
      targetKey: 'clue_id',
      normalize: createNormalizer('timeline_event', 'clue', 'timeline_event_id', 'clue_id'),
    },
  },
}

function getLinkSpec(sourceType: MaterialLinkTargetType, targetType: MaterialLinkTargetType): LinkApiSpec {
  const spec = linkApiRegistry[sourceType]?.[targetType]
  if (!spec) {
    throw new Error(`当前未支持 ${sourceType} -> ${targetType} 的统一关联接口。`)
  }
  return spec
}

export async function listLinks(
  sourceType: MaterialLinkTargetType,
  sourceId: string,
  targetType: MaterialLinkTargetType,
): Promise<MaterialLinkRelation[]> {
  const spec = getLinkSpec(sourceType, targetType)
  const items = await spec.list(sourceId)
  return items.map((item) => spec.normalize(item as Record<string, unknown>, sourceId))
}

export async function addLink(
  sourceType: MaterialLinkTargetType,
  sourceId: string,
  targetType: MaterialLinkTargetType,
  payload: MaterialLinkPayload & { target_id?: string },
): Promise<MaterialLinkRelation> {
  const spec = getLinkSpec(sourceType, targetType)
  const raw = await spec.add(sourceId, {
    [spec.targetKey]: payload.target_id ?? '',
    relation_type: payload.relation_type ?? 'related',
    note: payload.note ?? '',
  })
  return spec.normalize(raw as Record<string, unknown>, sourceId)
}

export function removeLink(
  sourceType: MaterialLinkTargetType,
  sourceId: string,
  targetType: MaterialLinkTargetType,
  targetId: string,
  options?: { linkId?: string },
): Promise<void> {
  const spec = getLinkSpec(sourceType, targetType)
  return spec.remove(sourceId, targetId, options?.linkId)
}

export function listTimelineEventCharacters(eventId: string): Promise<TimelineEventCharacterLink[]> {
  return apiRequest<TimelineEventCharacterLink[]>(`/api/timeline-events/${eventId}/characters`)
}

export function addTimelineEventCharacter(
  eventId: string,
  payload: TimelineEventCharacterLinkPayload,
): Promise<TimelineEventCharacterLink> {
  return apiRequest<TimelineEventCharacterLink>(`/api/timeline-events/${eventId}/characters`, {
    method: 'POST',
    body: payload,
  })
}

export function removeTimelineEventCharacter(
  eventId: string,
  characterId: string,
): Promise<void> {
  return apiRequest<void>(`/api/timeline-events/${eventId}/characters/${characterId}`, {
    method: 'DELETE',
  })
}

export function listTimelineEventSettings(eventId: string): Promise<TimelineEventSettingLink[]> {
  return apiRequest<TimelineEventSettingLink[]>(`/api/timeline-events/${eventId}/settings`)
}

export function addTimelineEventSetting(
  eventId: string,
  payload: TimelineEventSettingLinkPayload,
): Promise<TimelineEventSettingLink> {
  return apiRequest<TimelineEventSettingLink>(`/api/timeline-events/${eventId}/settings`, {
    method: 'POST',
    body: payload,
  })
}

export function removeTimelineEventSetting(eventId: string, settingId: string): Promise<void> {
  return apiRequest<void>(`/api/timeline-events/${eventId}/settings/${settingId}`, {
    method: 'DELETE',
  })
}

export function listTimelineEventClues(eventId: string): Promise<TimelineEventClueLink[]> {
  return apiRequest<TimelineEventClueLink[]>(`/api/timeline-events/${eventId}/clues`)
}

export function addTimelineEventClue(
  eventId: string,
  payload: TimelineEventClueLinkPayload,
): Promise<TimelineEventClueLink> {
  return apiRequest<TimelineEventClueLink>(`/api/timeline-events/${eventId}/clues`, {
    method: 'POST',
    body: payload,
  })
}

export function removeTimelineEventClue(eventId: string, clueId: string): Promise<void> {
  return apiRequest<void>(`/api/timeline-events/${eventId}/clues/${clueId}`, {
    method: 'DELETE',
  })
}

export function listOutlineCharacters(outlineItemId: string): Promise<OutlineCharacterLink[]> {
  return apiRequest<OutlineCharacterLink[]>(`/api/outlines/${outlineItemId}/characters`)
}

export function addOutlineCharacter(
  outlineItemId: string,
  payload: OutlineCharacterLinkPayload,
): Promise<OutlineCharacterLink> {
  return apiRequest<OutlineCharacterLink>(`/api/outlines/${outlineItemId}/characters`, {
    method: 'POST',
    body: payload,
  })
}

export function removeOutlineCharacter(
  outlineItemId: string,
  characterId: string,
): Promise<void> {
  return apiRequest<void>(`/api/outlines/${outlineItemId}/characters/${characterId}`, {
    method: 'DELETE',
  })
}

export function listOutlineSettings(outlineItemId: string): Promise<OutlineSettingLink[]> {
  return apiRequest<OutlineSettingLink[]>(`/api/outlines/${outlineItemId}/settings`)
}

export function addOutlineSetting(
  outlineItemId: string,
  payload: OutlineSettingLinkPayload,
): Promise<OutlineSettingLink> {
  return apiRequest<OutlineSettingLink>(`/api/outlines/${outlineItemId}/settings`, {
    method: 'POST',
    body: payload,
  })
}

export function removeOutlineSetting(outlineItemId: string, settingId: string): Promise<void> {
  return apiRequest<void>(`/api/outlines/${outlineItemId}/settings/${settingId}`, {
    method: 'DELETE',
  })
}

export function listOutlineClues(outlineItemId: string): Promise<OutlineClueLink[]> {
  return apiRequest<OutlineClueLink[]>(`/api/outlines/${outlineItemId}/clues`)
}

export function addOutlineClue(
  outlineItemId: string,
  payload: OutlineClueLinkPayload,
): Promise<OutlineClueLink> {
  return apiRequest<OutlineClueLink>(`/api/outlines/${outlineItemId}/clues`, {
    method: 'POST',
    body: payload,
  })
}

export function removeOutlineClue(outlineItemId: string, clueId: string): Promise<void> {
  return apiRequest<void>(`/api/outlines/${outlineItemId}/clues/${clueId}`, {
    method: 'DELETE',
  })
}

export function listOutlineTimelineEvents(
  outlineItemId: string,
): Promise<OutlineTimelineEventLink[]> {
  return apiRequest<OutlineTimelineEventLink[]>(`/api/outlines/${outlineItemId}/timeline-events`)
}

export function addOutlineTimelineEvent(
  outlineItemId: string,
  payload: OutlineTimelineEventLinkPayload,
): Promise<OutlineTimelineEventLink> {
  return apiRequest<OutlineTimelineEventLink>(`/api/outlines/${outlineItemId}/timeline-events`, {
    method: 'POST',
    body: payload,
  })
}

export function removeOutlineTimelineEvent(
  outlineItemId: string,
  eventId: string,
): Promise<void> {
  return apiRequest<void>(`/api/outlines/${outlineItemId}/timeline-events/${eventId}`, {
    method: 'DELETE',
  })
}

export function getMaterialLinkSummary(projectId: string): Promise<MaterialLinkSummary> {
  return apiRequest<MaterialLinkSummary>(`/api/projects/${projectId}/material-links/summary`)
}

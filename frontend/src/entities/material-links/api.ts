import { apiRequest } from '@/shared/api/client'

import type {
  MaterialLinkSummary,
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

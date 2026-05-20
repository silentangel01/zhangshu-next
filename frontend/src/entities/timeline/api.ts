import { apiRequest } from '@/shared/api/client'

import type {
  CreateTimelineEventPayload,
  TimelineEvent,
  TimelineFilters,
  UpdateTimelineEventPayload,
} from './types'

function buildQuery(filters?: TimelineFilters): string {
  if (!filters) {
    return ''
  }

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      params.set(key, value)
    }
  }

  const query = params.toString()
  return query ? `?${query}` : ''
}

export function listProjectTimelineEvents(
  projectId: string,
  filters?: TimelineFilters,
): Promise<TimelineEvent[]> {
  return apiRequest<TimelineEvent[]>(`/api/projects/${projectId}/timeline-events${buildQuery(filters)}`)
}

export function createTimelineEvent(
  projectId: string,
  payload: CreateTimelineEventPayload,
): Promise<TimelineEvent> {
  return apiRequest<TimelineEvent>(`/api/projects/${projectId}/timeline-events`, {
    method: 'POST',
    body: payload,
  })
}

export function getTimelineEvent(eventId: string): Promise<TimelineEvent> {
  return apiRequest<TimelineEvent>(`/api/timeline-events/${eventId}`)
}

export function updateTimelineEvent(
  eventId: string,
  payload: UpdateTimelineEventPayload,
): Promise<TimelineEvent> {
  return apiRequest<TimelineEvent>(`/api/timeline-events/${eventId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteTimelineEvent(eventId: string): Promise<TimelineEvent> {
  return apiRequest<TimelineEvent>(`/api/timeline-events/${eventId}`, {
    method: 'DELETE',
  })
}

export function listChapterTimelineEvents(chapterId: string): Promise<TimelineEvent[]> {
  return apiRequest<TimelineEvent[]>(`/api/chapters/${chapterId}/timeline-events`)
}

import { apiRequest } from '@/shared/api/client'

import type {
  CreateTimelineEdgePayload,
  CreateTimelineEventPayload,
  CreateTimelineTrackPayload,
  TimelineEdge,
  TimelineEdgeFilters,
  TimelineEvent,
  TimelineFilters,
  TimelineTrack,
  UpdateTimelineEdgePayload,
  UpdateTimelineEventPayload,
  UpdateTimelineTrackPayload,
} from './types'

function buildQuery(parameters?: object): string {
  if (!parameters) {
    return ''
  }

  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(parameters as Record<string, unknown>)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }

  const query = search.toString()
  return query ? `?${query}` : ''
}

export function listTimelineTracks(projectId: string): Promise<TimelineTrack[]> {
  return apiRequest<TimelineTrack[]>(`/api/projects/${projectId}/timeline-tracks`)
}

export function createTimelineTrack(
  projectId: string,
  payload: CreateTimelineTrackPayload,
): Promise<TimelineTrack> {
  return apiRequest<TimelineTrack>(`/api/projects/${projectId}/timeline-tracks`, {
    method: 'POST',
    body: payload,
  })
}

export function getTimelineTrack(trackId: string): Promise<TimelineTrack> {
  return apiRequest<TimelineTrack>(`/api/timeline-tracks/${trackId}`)
}

export function updateTimelineTrack(
  trackId: string,
  payload: UpdateTimelineTrackPayload,
): Promise<TimelineTrack> {
  return apiRequest<TimelineTrack>(`/api/timeline-tracks/${trackId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteTimelineTrack(trackId: string): Promise<TimelineTrack> {
  return apiRequest<TimelineTrack>(`/api/timeline-tracks/${trackId}`, {
    method: 'DELETE',
  })
}

export function listProjectTimelineEvents(
  projectId: string,
  filters?: TimelineFilters,
): Promise<TimelineEvent[]> {
  return apiRequest<TimelineEvent[]>(
    `/api/projects/${projectId}/timeline-events${buildQuery(filters)}`,
  )
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

export function listTimelineEdges(
  projectId: string,
  filters?: TimelineEdgeFilters,
): Promise<TimelineEdge[]> {
  return apiRequest<TimelineEdge[]>(
    `/api/projects/${projectId}/timeline-edges${buildQuery(filters)}`,
  )
}

export function createTimelineEdge(
  projectId: string,
  payload: CreateTimelineEdgePayload,
): Promise<TimelineEdge> {
  return apiRequest<TimelineEdge>(`/api/projects/${projectId}/timeline-edges`, {
    method: 'POST',
    body: payload,
  })
}

export function getTimelineEdge(edgeId: string): Promise<TimelineEdge> {
  return apiRequest<TimelineEdge>(`/api/timeline-edges/${edgeId}`)
}

export function updateTimelineEdge(
  edgeId: string,
  payload: UpdateTimelineEdgePayload,
): Promise<TimelineEdge> {
  return apiRequest<TimelineEdge>(`/api/timeline-edges/${edgeId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteTimelineEdge(edgeId: string): Promise<TimelineEdge> {
  return apiRequest<TimelineEdge>(`/api/timeline-edges/${edgeId}`, {
    method: 'DELETE',
  })
}

export function listChapterTimelineEvents(chapterId: string): Promise<TimelineEvent[]> {
  return apiRequest<TimelineEvent[]>(`/api/chapters/${chapterId}/timeline-events`)
}

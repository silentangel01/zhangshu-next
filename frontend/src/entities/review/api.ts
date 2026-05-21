import { apiRequest } from '@/shared/api/client'

import type {
  ProhibitedTerm,
  ProhibitedTermPayload,
  ProhibitedTermUpdatePayload,
  ReviewCheckPayload,
  ReviewCheckResponse,
} from './types'

export function listProhibitedTerms(): Promise<ProhibitedTerm[]> {
  return apiRequest<ProhibitedTerm[]>('/api/review/prohibited-terms')
}

export function createProhibitedTerm(payload: ProhibitedTermPayload): Promise<ProhibitedTerm> {
  return apiRequest<ProhibitedTerm>('/api/review/prohibited-terms', {
    method: 'POST',
    body: payload,
  })
}

export function updateProhibitedTerm(
  termId: string,
  payload: ProhibitedTermUpdatePayload,
): Promise<ProhibitedTerm> {
  return apiRequest<ProhibitedTerm>(`/api/review/prohibited-terms/${termId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteProhibitedTerm(termId: string): Promise<void> {
  return apiRequest<void>(`/api/review/prohibited-terms/${termId}`, {
    method: 'DELETE',
  })
}

export function runReviewCheck(
  projectId: string,
  payload: ReviewCheckPayload,
): Promise<ReviewCheckResponse> {
  return apiRequest<ReviewCheckResponse>(`/api/projects/${projectId}/review/check`, {
    method: 'POST',
    body: payload,
  })
}

export function listReviewResults(projectId: string): Promise<ReviewCheckResponse> {
  return apiRequest<ReviewCheckResponse>(`/api/projects/${projectId}/review/results`)
}

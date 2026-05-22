import { API_BASE_URL, ApiError, apiRequest } from '@/shared/api/client'

import type {
  ProhibitedTerm,
  ProhibitedTermImportReport,
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

export async function exportProhibitedTerms(): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/review/prohibited-terms/export`)
  if (!response.ok) {
    throw new ApiError(`API request failed: ${response.status}`, response.status)
  }
  return response.blob()
}

export async function importProhibitedTerms(file: File): Promise<ProhibitedTermImportReport> {
  const formData = new FormData()
  formData.set('file', file)
  const response = await fetch(`${API_BASE_URL}/api/review/prohibited-terms/import`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let message = `API request failed: ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      }
    } catch {
      // Keep the status-based message when the API does not return JSON.
    }
    throw new ApiError(message, response.status)
  }

  return response.json() as Promise<ProhibitedTermImportReport>
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

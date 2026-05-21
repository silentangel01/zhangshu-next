import { apiRequest } from '@/shared/api/client'

import type { ProjectSearchResponse } from './types'

export function searchProjectChapters(
  projectId: string,
  query: string,
): Promise<ProjectSearchResponse> {
  const params = new URLSearchParams({ q: query })
  return apiRequest<ProjectSearchResponse>(`/api/projects/${projectId}/search?${params.toString()}`)
}

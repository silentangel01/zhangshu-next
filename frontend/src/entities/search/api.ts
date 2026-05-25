import { apiRequest } from '@/shared/api/client'

import type {
  ProjectSearchResponse,
  RebuildSearchIndexResponse,
  SearchEntityType,
} from './types'

export function searchProject(
  projectId: string,
  query: string,
  options?: {
    types?: SearchEntityType[]
    limit?: number
    offset?: number
  },
): Promise<ProjectSearchResponse> {
  const params = new URLSearchParams({ q: query })
  if (options?.types && options.types.length > 0) {
    params.set('types', options.types.join(','))
  }
  if (options?.limit != null) {
    params.set('limit', String(options.limit))
  }
  if (options?.offset != null) {
    params.set('offset', String(options.offset))
  }
  return apiRequest<ProjectSearchResponse>(
    `/api/projects/${projectId}/search?${params.toString()}`,
  )
}

/** @deprecated Use searchProject instead */
export function searchProjectChapters(
  projectId: string,
  query: string,
): Promise<ProjectSearchResponse> {
  return searchProject(projectId, query, { types: ['chapter'] })
}

export function rebuildProjectSearchIndex(
  projectId: string,
): Promise<RebuildSearchIndexResponse> {
  return apiRequest<RebuildSearchIndexResponse>(
    `/api/projects/${projectId}/search-index/rebuild`,
    { method: 'POST' },
  )
}

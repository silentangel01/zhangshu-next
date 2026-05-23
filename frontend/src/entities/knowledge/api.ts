import { apiRequest, apiUpload } from '@/shared/api/client'

import type {
  CreateKnowledgeLinkPayload,
  CreateKnowledgeSourcePayload,
  KnowledgeAskRequest,
  KnowledgeAskResponse,
  KnowledgeBuildSourceEmbeddingsResponse,
  KnowledgeChunk,
  KnowledgeCredibility,
  KnowledgeImportPreview,
  KnowledgeImportResult,
  KnowledgeIndexStatus,
  KnowledgeLink,
  KnowledgeRebuildIndexResponse,
  KnowledgeRetrievalFilters,
  KnowledgeRetrievalResponse,
  KnowledgeSource,
  KnowledgeSourceFilters,
  KnowledgeSourceList,
  KnowledgeSourceType,
  KnowledgeSummaryRequest,
  KnowledgeSummaryResponse,
  UpdateKnowledgeSourcePayload,
} from './types'

function buildQuery(filters?: KnowledgeSourceFilters): string {
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

export function listKnowledgeSources(
  projectId: string,
  filters?: KnowledgeSourceFilters,
): Promise<KnowledgeSourceList> {
  return apiRequest<KnowledgeSourceList>(
    `/api/projects/${projectId}/knowledge-sources${buildQuery(filters)}`,
  )
}

export function createKnowledgeSource(
  projectId: string,
  payload: CreateKnowledgeSourcePayload,
): Promise<KnowledgeSource> {
  return apiRequest<KnowledgeSource>(`/api/projects/${projectId}/knowledge-sources`, {
    method: 'POST',
    body: payload,
  })
}

export function getKnowledgeSource(sourceId: string): Promise<KnowledgeSource> {
  return apiRequest<KnowledgeSource>(`/api/knowledge-sources/${sourceId}`)
}

export function updateKnowledgeSource(
  sourceId: string,
  payload: UpdateKnowledgeSourcePayload,
): Promise<KnowledgeSource> {
  return apiRequest<KnowledgeSource>(`/api/knowledge-sources/${sourceId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteKnowledgeSource(sourceId: string): Promise<KnowledgeSource> {
  return apiRequest<KnowledgeSource>(`/api/knowledge-sources/${sourceId}`, {
    method: 'DELETE',
  })
}

export function listKnowledgeChunks(sourceId: string): Promise<KnowledgeChunk[]> {
  return apiRequest<KnowledgeChunk[]>(`/api/knowledge-sources/${sourceId}/chunks`)
}

export function rebuildKnowledgeChunks(sourceId: string): Promise<KnowledgeChunk[]> {
  return apiRequest<KnowledgeChunk[]>(`/api/knowledge-sources/${sourceId}/rebuild-chunks`, {
    method: 'POST',
  })
}

export function listKnowledgeLinks(sourceId: string): Promise<KnowledgeLink[]> {
  return apiRequest<KnowledgeLink[]>(`/api/knowledge-sources/${sourceId}/links`)
}

export function createKnowledgeLink(
  sourceId: string,
  payload: CreateKnowledgeLinkPayload,
): Promise<KnowledgeLink> {
  return apiRequest<KnowledgeLink>(`/api/knowledge-sources/${sourceId}/links`, {
    method: 'POST',
    body: payload,
  })
}

export function deleteKnowledgeLink(linkId: string): Promise<KnowledgeLink> {
  return apiRequest<KnowledgeLink>(`/api/knowledge-links/${linkId}`, {
    method: 'DELETE',
  })
}

// --- Knowledge Import ---

export function previewKnowledgeImport(
  projectId: string,
  files: File[],
): Promise<KnowledgeImportPreview> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  return apiUpload<KnowledgeImportPreview>(
    `/api/projects/${projectId}/knowledge/import/preview`,
    formData,
    { method: 'POST' },
  )
}

export function confirmKnowledgeImport(
  projectId: string,
  files: File[],
  options?: {
    sourceType?: KnowledgeSourceType
    credibility?: KnowledgeCredibility
    tags?: string
  },
): Promise<KnowledgeImportResult> {
  const params = new URLSearchParams()
  if (options?.sourceType) params.set('source_type', options.sourceType)
  if (options?.credibility) params.set('credibility', options.credibility)
  if (options?.tags) params.set('tags', options.tags)

  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const query = params.toString()
  const querySuffix = query ? `?${query}` : ''
  return apiUpload<KnowledgeImportResult>(
    `/api/projects/${projectId}/knowledge/import/confirm${querySuffix}`,
    formData,
    { method: 'POST' },
  )
}

// --- Knowledge Retrieval ---

export function searchKnowledgeChunks(
  projectId: string,
  keyword: string,
  filters?: KnowledgeRetrievalFilters,
): Promise<KnowledgeRetrievalResponse> {
  const params = new URLSearchParams()
  params.set('keyword', keyword)

  if (filters?.source_type) params.set('source_type', filters.source_type)
  if (filters?.credibility) params.set('credibility', filters.credibility)
  if (filters?.tag) params.set('tag', filters.tag)
  if (filters?.source_id) params.set('source_id', filters.source_id)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.mode) params.set('mode', filters.mode)

  const query = params.toString()
  return apiRequest<KnowledgeRetrievalResponse>(
    `/api/projects/${projectId}/knowledge/search?${query}`,
  )
}

// --- Knowledge Embedding Index ---

export function getKnowledgeIndexStatus(
  projectId: string,
): Promise<KnowledgeIndexStatus> {
  return apiRequest<KnowledgeIndexStatus>(
    `/api/projects/${projectId}/knowledge/embeddings/status`,
  )
}

export function rebuildKnowledgeIndex(
  projectId: string,
): Promise<KnowledgeRebuildIndexResponse> {
  return apiRequest<KnowledgeRebuildIndexResponse>(
    `/api/projects/${projectId}/knowledge/embeddings/rebuild`,
    { method: 'POST' },
  )
}

export function buildSourceEmbeddings(
  sourceId: string,
): Promise<KnowledgeBuildSourceEmbeddingsResponse> {
  return apiRequest<KnowledgeBuildSourceEmbeddingsResponse>(
    `/api/knowledge-sources/${sourceId}/embeddings`,
    { method: 'POST' },
  )
}

// --- RAG (Ask & Summary) ---

export function askKnowledgeBase(
  projectId: string,
  payload: KnowledgeAskRequest,
): Promise<KnowledgeAskResponse> {
  return apiRequest<KnowledgeAskResponse>(
    `/api/projects/${projectId}/knowledge/ask`,
    { method: 'POST', body: payload },
  )
}

export function summarizeKnowledge(
  projectId: string,
  payload: KnowledgeSummaryRequest,
): Promise<KnowledgeSummaryResponse> {
  return apiRequest<KnowledgeSummaryResponse>(
    `/api/projects/${projectId}/knowledge/summary`,
    { method: 'POST', body: payload },
  )
}

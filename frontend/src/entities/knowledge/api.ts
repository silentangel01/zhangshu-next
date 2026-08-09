import { apiRequest, apiUpload } from '@/shared/api/client'

import type {
  CreateKnowledgeLinkPayload,
  CreateKnowledgeGraphExtractionRunPayload,
  CreateKnowledgeSourcePayload,
  EmbeddingProviderListResponse,
  IndexProfile,
  KnowledgeAskRequest,
  KnowledgeAskResponse,
  KnowledgeBuildSourceEmbeddingsResponse,
  KnowledgeChunk,
  KnowledgeCredibility,
  KnowledgeGraphEntity,
  KnowledgeGraphEntityList,
  KnowledgeGraphExtractionRun,
  KnowledgeGraphFactStatus,
  KnowledgeGraphRelation,
  KnowledgeGraphRelationList,
  KnowledgeGraphRelationType,
  KnowledgeGraphRunList,
  KnowledgeGraphStatus,
  KnowledgeGraphSubgraph,
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
  RefreshKnowledgeIndexPayload,
  RefreshKnowledgeIndexResponse,
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

export function getUploadFilename(file: File): string {
  return file.webkitRelativePath || file.name
}

export function previewKnowledgeImport(
  projectId: string,
  files: File[],
): Promise<KnowledgeImportPreview> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file, getUploadFilename(file))
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
    formData.append('files', file, getUploadFilename(file))
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
  if (filters?.strictness) params.set('strictness', filters.strictness)

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

export function refreshKnowledgeIndex(
  projectId: string,
  payload: RefreshKnowledgeIndexPayload,
): Promise<RefreshKnowledgeIndexResponse> {
  return apiRequest<RefreshKnowledgeIndexResponse>(
    `/api/projects/${projectId}/knowledge/index/refresh`,
    { method: 'POST', body: payload },
  )
}

export function listEmbeddingProviders(
  projectId: string,
): Promise<EmbeddingProviderListResponse> {
  return apiRequest<EmbeddingProviderListResponse>(
    `/api/projects/${projectId}/knowledge/embedding-providers`,
  )
}

export function getKnowledgeIndexProfile(
  projectId: string,
): Promise<IndexProfile> {
  return apiRequest<IndexProfile>(
    `/api/projects/${projectId}/knowledge/index-profile`,
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

// --- Knowledge Graph ---

function buildKnowledgeGraphQuery(
  filters?: Record<string, string | number | null | undefined>,
): string {
  if (!filters) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function createKnowledgeGraphExtractionRun(
  projectId: string,
  payload: CreateKnowledgeGraphExtractionRunPayload,
): Promise<KnowledgeGraphExtractionRun> {
  return apiRequest<KnowledgeGraphExtractionRun>(
    `/api/projects/${projectId}/knowledge-graph/extraction-runs`,
    { method: 'POST', body: payload },
  )
}

export function listKnowledgeGraphExtractionRuns(
  projectId: string,
  limit = 20,
): Promise<KnowledgeGraphRunList> {
  return apiRequest<KnowledgeGraphRunList>(
    `/api/projects/${projectId}/knowledge-graph/extraction-runs${buildKnowledgeGraphQuery({ limit })}`,
  )
}

export function listKnowledgeGraphEntities(
  projectId: string,
  filters?: {
    status?: KnowledgeGraphStatus
    entity_type?: string
    keyword?: string
    limit?: number
  },
): Promise<KnowledgeGraphEntityList> {
  return apiRequest<KnowledgeGraphEntityList>(
    `/api/projects/${projectId}/knowledge-graph/entities${buildKnowledgeGraphQuery(filters)}`,
  )
}

export function listKnowledgeGraphRelations(
  projectId: string,
  filters?: {
    status?: KnowledgeGraphStatus
    entity_id?: string
    relation_type?: KnowledgeGraphRelationType
    fact_status?: KnowledgeGraphFactStatus
    source_id?: string
    limit?: number
  },
): Promise<KnowledgeGraphRelationList> {
  return apiRequest<KnowledgeGraphRelationList>(
    `/api/projects/${projectId}/knowledge-graph/relations${buildKnowledgeGraphQuery(filters)}`,
  )
}

export function acceptKnowledgeGraphEntity(
  projectId: string,
  entityId: string,
): Promise<KnowledgeGraphEntity> {
  return apiRequest<KnowledgeGraphEntity>(
    `/api/projects/${projectId}/knowledge-graph/entities/${entityId}/accept`,
    { method: 'POST' },
  )
}

export function rejectKnowledgeGraphEntity(
  projectId: string,
  entityId: string,
): Promise<KnowledgeGraphEntity> {
  return apiRequest<KnowledgeGraphEntity>(
    `/api/projects/${projectId}/knowledge-graph/entities/${entityId}/reject`,
    { method: 'POST' },
  )
}

export function acceptKnowledgeGraphRelation(
  projectId: string,
  relationId: string,
): Promise<KnowledgeGraphRelation> {
  return apiRequest<KnowledgeGraphRelation>(
    `/api/projects/${projectId}/knowledge-graph/relations/${relationId}/accept`,
    { method: 'POST' },
  )
}

export function rejectKnowledgeGraphRelation(
  projectId: string,
  relationId: string,
): Promise<KnowledgeGraphRelation> {
  return apiRequest<KnowledgeGraphRelation>(
    `/api/projects/${projectId}/knowledge-graph/relations/${relationId}/reject`,
    { method: 'POST' },
  )
}

export function getKnowledgeGraphSubgraph(
  projectId: string,
  filters?: {
    status?: KnowledgeGraphStatus
    entity_id?: string
    limit?: number
  },
): Promise<KnowledgeGraphSubgraph> {
  return apiRequest<KnowledgeGraphSubgraph>(
    `/api/projects/${projectId}/knowledge-graph/subgraph${buildKnowledgeGraphQuery(filters)}`,
  )
}

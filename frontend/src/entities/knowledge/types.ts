export type KnowledgeSourceType = 'note' | 'file' | 'webpage' | 'book' | 'quote' | 'custom'

export type KnowledgeSourceStatus = 'active' | 'archived'

export type KnowledgeCredibility = 'low' | 'normal' | 'high'

export type KnowledgeLinkTargetType =
  | 'project'
  | 'chapter'
  | 'character'
  | 'setting'
  | 'clue'
  | 'timeline_event'
  | 'graph_node'

export type KnowledgeLinkRelationType =
  | 'reference'
  | 'inspiration'
  | 'evidence'
  | 'background'
  | 'related'

export interface KnowledgeSource {
  id: string
  project_id: string
  title: string
  source_type: KnowledgeSourceType
  source_uri: string
  author: string | null
  summary: string
  content: string
  tags: string
  status: KnowledgeSourceStatus
  credibility: KnowledgeCredibility
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface KnowledgeChunk {
  id: string
  project_id: string
  source_id: string
  chunk_index: number
  heading: string
  content: string
  token_count: number
  metadata_json: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface KnowledgeLink {
  id: string
  project_id: string
  source_id: string
  chunk_id: string | null
  target_type: KnowledgeLinkTargetType
  target_id: string
  relation_type: KnowledgeLinkRelationType
  note: string
  created_at: string
  deleted_at: string | null
}

export interface KnowledgeSourceList {
  total: number
  items: KnowledgeSource[]
}

export interface KnowledgeSourcePayload {
  title: string
  source_type?: KnowledgeSourceType
  source_uri?: string
  author?: string | null
  summary?: string
  content?: string
  tags?: string
  status?: KnowledgeSourceStatus
  credibility?: KnowledgeCredibility
}

export type CreateKnowledgeSourcePayload = KnowledgeSourcePayload
export type UpdateKnowledgeSourcePayload = Partial<KnowledgeSourcePayload>

export interface KnowledgeSourceFilters {
  keyword?: string
  source_type?: KnowledgeSourceType
  status?: KnowledgeSourceStatus
  tag?: string
  credibility?: KnowledgeCredibility
}

export interface CreateKnowledgeLinkPayload {
  chunk_id?: string | null
  target_type: KnowledgeLinkTargetType
  target_id: string
  relation_type?: KnowledgeLinkRelationType
  note?: string
}

export const knowledgeSourceTypeLabels: Record<KnowledgeSourceType, string> = {
  note: '笔记',
  file: '文件',
  webpage: '网页',
  book: '书籍',
  quote: '引用',
  custom: '自定义',
}

export const knowledgeSourceStatusLabels: Record<KnowledgeSourceStatus, string> = {
  active: '活跃',
  archived: '归档',
}

export const knowledgeCredibilityLabels: Record<KnowledgeCredibility, string> = {
  low: '低',
  normal: '一般',
  high: '高',
}

export const knowledgeLinkRelationTypeLabels: Record<KnowledgeLinkRelationType, string> = {
  reference: '参考',
  inspiration: '灵感',
  evidence: '证据',
  background: '背景',
  related: '相关',
}

export const knowledgeLinkTargetTypeLabels: Record<KnowledgeLinkTargetType, string> = {
  project: '项目',
  chapter: '章节',
  character: '人物',
  setting: '设定',
  clue: '伏笔',
  timeline_event: '时间线事件',
  graph_node: '关系图节点',
}

// --- Knowledge Import ---

export interface KnowledgeImportDocument {
  title: string
  content: string
  source_type: KnowledgeSourceType
  source_uri: string
  filename: string
  word_count: number
}

export interface KnowledgeImportPreview {
  documents: KnowledgeImportDocument[]
  document_count: number
  total_word_count: number
  warnings: string[]
  failed_files: string[]
  empty_files: string[]
  unsupported_files: string[]
  can_import: boolean
}

export interface KnowledgeImportedSource {
  id: string
  title: string
  source_type: KnowledgeSourceType
  chunk_count: number
}

export interface KnowledgeImportResult {
  imported_count: number
  imported_sources: KnowledgeImportedSource[]
  warnings: string[]
  failed_files: string[]
  empty_files: string[]
  unsupported_files: string[]
}

// --- Knowledge Retrieval ---

export type KnowledgeSearchMode = 'keyword' | 'semantic' | 'hybrid'

export interface KnowledgeRetrievalFilters {
  source_type?: KnowledgeSourceType
  credibility?: KnowledgeCredibility
  tag?: string
  source_id?: string
  limit?: number
  mode?: KnowledgeSearchMode
}

export interface KnowledgeRetrievalChunkResult {
  chunk_id: string
  chunk_index: number
  chunk_heading: string
  chunk_content: string
  matched_snippet: string
  context_before: string
  context_after: string
  source_id: string
  source_title: string
  source_type: KnowledgeSourceType
  source_credibility: KnowledgeCredibility
  relevance_score?: number | null
}

export interface KnowledgeRetrievalResponse {
  keyword: string
  total: number
  results: KnowledgeRetrievalChunkResult[]
  mode: string
}

// --- Knowledge Embedding Index ---

export interface KnowledgeIndexStatus {
  total_chunks: number
  indexed_chunks: number
  unindexed_chunks: number
  model_name: string
}

export interface KnowledgeRebuildIndexResponse {
  indexed_count: number
  model_name: string
}

export interface KnowledgeBuildSourceEmbeddingsResponse {
  indexed_count: number
  source_id: string
  model_name: string
}

// --- RAG (Ask & Summary) ---

export interface KnowledgeAskRequest {
  question: string
  mode?: KnowledgeSearchMode
  source_type?: KnowledgeSourceType
  credibility?: KnowledgeCredibility
  top_k?: number
}

export interface RagCitation {
  chunk_id: string
  source_id: string
  source_title: string
  chunk_heading: string
  chunk_content: string
  relevance_score?: number | null
}

export interface KnowledgeAskResponse {
  question: string
  answer: string
  citations: RagCitation[]
  model: string
  retrieval_mode: string
}

export interface KnowledgeSummaryRequest {
  topic?: string
  source_ids?: string[]
  mode?: KnowledgeSearchMode
}

export interface KnowledgeSummaryResponse {
  summary: string
  sources_used: number
  source_titles: string[]
  model: string
  is_draft: boolean
}

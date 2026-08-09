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
  relative_path: string
  extension: string
  word_count: number
  size: number
}

export interface KnowledgeImportPreview {
  documents: KnowledgeImportDocument[]
  document_count: number
  supported_count: number
  unsupported_count: number
  total_word_count: number
  total_size: number
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

export type KnowledgeRetrievalStrictness = 'strict' | 'balanced' | 'broad'

export const knowledgeRetrievalStrictnessLabels: Record<KnowledgeRetrievalStrictness, string> = {
  strict: '精准',
  balanced: '均衡',
  broad: '宽泛',
}

export interface KnowledgeRetrievalFilters {
  source_type?: KnowledgeSourceType
  credibility?: KnowledgeCredibility
  tag?: string
  source_id?: string
  limit?: number
  mode?: KnowledgeSearchMode
  strictness?: KnowledgeRetrievalStrictness
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
  vector_score?: number | null
  keyword_score?: number | null
  final_score?: number | null
  match_quality?: string | null
  match_reason?: string | null
}

export interface KnowledgeRetrievalResponse {
  keyword: string
  total: number
  results: KnowledgeRetrievalChunkResult[]
  mode: string
  strictness?: string
  candidate_count?: number
  filtered_count?: number
  warnings?: string[]
}

// --- Knowledge Embedding Index ---

export interface KnowledgeIndexStatus {
  total_chunks: number
  indexed_chunks: number
  unindexed_chunks: number
  model_name: string
  provider_id: string | null
  provider_type: string | null
  display_name: string | null
  vector_dim: number | null
  chunk_size: string | null
  profile_status: string
  last_refreshed_at: string | null
  last_error: string | null
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

// --- Knowledge Index Refresh ---

export type KnowledgeChunkSize = 'small' | 'medium' | 'large'

export type KnowledgeIndexRefreshScope = 'project' | 'source'

export interface RefreshKnowledgeIndexPayload {
  scope: KnowledgeIndexRefreshScope
  source_id?: string | null
  chunk_size: KnowledgeChunkSize
  provider_id?: string | null
  privacy_confirmed?: boolean
}

export interface RefreshKnowledgeIndexResponse {
  source_count: number
  chunk_count: number
  indexed_count: number
  chunk_size: KnowledgeChunkSize
  model_name: string
  provider_id: string
  warnings: string[]
}

export const knowledgeChunkSizeLabels: Record<KnowledgeChunkSize, string> = {
  small: '小',
  medium: '中',
  large: '大',
}

export const knowledgeChunkSizeDescriptions: Record<KnowledgeChunkSize, string> = {
  small: '更容易命中细节，但内容会被切得更碎，搜索结果可能重复，刷新耗时和索引占用会增加。',
  medium: '适合大多数小说资料，兼顾细节命中和上下文完整度。',
  large: '能保留更完整上下文，但细节命中可能下降，问答时可能带入较长无关内容。',
}

// --- Embedding Provider ---

export type EmbeddingProviderType = 'local' | 'cloud' | 'compat'

export interface EmbeddingProviderInfo {
  id: string
  display_name: string
  provider_type: EmbeddingProviderType
  model_name: string
  vector_dim: number
  available: boolean
  reason: string
  requires_privacy_confirm: boolean
  requires_network: boolean
  quality_label: string
  description: string
}

export interface EmbeddingProviderListResponse {
  providers: EmbeddingProviderInfo[]
  default_provider_id: string
}

export interface IndexProfile {
  provider_id: string | null
  provider_type: string | null
  display_name: string | null
  model_name: string | null
  vector_dim: number | null
  chunk_size: string | null
  status: string | null
  last_refreshed_at: string | null
  last_error: string | null
}

// --- RAG (Ask & Summary) ---

export interface KnowledgeAskRequest {
  question: string
  mode?: KnowledgeSearchMode
  source_type?: KnowledgeSourceType
  credibility?: KnowledgeCredibility
  top_k?: number
  strictness?: KnowledgeRetrievalStrictness
}

export interface RagCitation {
  chunk_id: string
  source_id: string
  source_title: string
  chunk_heading: string
  chunk_content: string
  relevance_score?: number | null
  match_quality?: string | null
}

export interface KnowledgeAskResponse {
  question: string
  answer: string
  citations: RagCitation[]
  model: string
  retrieval_mode: string
  retrieval_warning?: string | null
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
  warnings?: string[]
}

// --- Knowledge Graph ---

export type KnowledgeGraphStatus = 'candidate' | 'accepted' | 'rejected'

export type KnowledgeGraphExtractionStatus = 'pending' | 'running' | 'completed' | 'failed'

export type KnowledgeGraphExtractionScope = 'project' | 'source'

export type KnowledgeGraphEntityType =
  | 'character'
  | 'setting'
  | 'location'
  | 'organization'
  | 'item'
  | 'event'
  | 'clue'
  | 'concept'
  | 'custom'

export type KnowledgeGraphRelationType =
  | 'relationship'
  | 'conflict'
  | 'ally'
  | 'family'
  | 'belongs_to'
  | 'located_in'
  | 'controls'
  | 'causes'
  | 'reveals'
  | 'foreshadows'
  | 'setting_related'
  | 'timeline_related'
  | 'custom'

export type KnowledgeGraphFactStatus =
  | 'confirmed'
  | 'claimed'
  | 'rumor'
  | 'hypothesis'
  | 'dream'
  | 'plan'
  | 'deprecated'

export interface KnowledgeGraphExtractionRun {
  id: string
  project_id: string
  scope: KnowledgeGraphExtractionScope
  source_id: string | null
  status: KnowledgeGraphExtractionStatus
  model_name: string
  total_chunks: number
  processed_chunks: number
  candidate_entity_count: number
  candidate_relation_count: number
  error_message: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  deleted_at: string | null
}

export interface KnowledgeGraphRunList {
  total: number
  items: KnowledgeGraphExtractionRun[]
}

export interface CreateKnowledgeGraphExtractionRunPayload {
  scope: KnowledgeGraphExtractionScope
  source_id?: string | null
  max_chunks?: number
  privacy_confirmed?: boolean
}

export interface KnowledgeGraphEntity {
  id: string
  project_id: string
  canonical_name: string
  entity_type: KnowledgeGraphEntityType
  aliases_json: string
  description: string
  bound_type: string | null
  bound_id: string | null
  status: KnowledgeGraphStatus
  confidence: number
  source_count: number
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface KnowledgeGraphEntityList {
  total: number
  items: KnowledgeGraphEntity[]
}

export interface KnowledgeGraphEvidence {
  id: string
  project_id: string
  entity_id: string | null
  relation_id: string | null
  source_id: string
  source_title: string
  chunk_id: string | null
  chunk_heading: string
  evidence_text: string
  char_start: number | null
  char_end: number | null
  extraction_run_id: string | null
  created_at: string
  deleted_at: string | null
}

export interface KnowledgeGraphRelation {
  id: string
  project_id: string
  subject_entity_id: string
  object_entity_id: string
  relation_type: KnowledgeGraphRelationType
  predicate_text: string
  direction: string
  fact_status: KnowledgeGraphFactStatus
  status: KnowledgeGraphStatus
  confidence: number
  note: string
  source_count: number
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
  subject: KnowledgeGraphEntity
  object: KnowledgeGraphEntity
  evidence: KnowledgeGraphEvidence[]
}

export interface KnowledgeGraphRelationList {
  total: number
  items: KnowledgeGraphRelation[]
}

export interface KnowledgeGraphSubgraphNode {
  id: string
  label: string
  entity_type: KnowledgeGraphEntityType
  status: KnowledgeGraphStatus
  confidence: number
}

export interface KnowledgeGraphSubgraphEdge {
  id: string
  source: string
  target: string
  label: string
  relation_type: KnowledgeGraphRelationType
  fact_status: KnowledgeGraphFactStatus
  confidence: number
}

export interface KnowledgeGraphSubgraph {
  nodes: KnowledgeGraphSubgraphNode[]
  edges: KnowledgeGraphSubgraphEdge[]
}

export const knowledgeGraphStatusLabels: Record<KnowledgeGraphStatus, string> = {
  candidate: '候选',
  accepted: '已确认',
  rejected: '已忽略',
}

export const knowledgeGraphExtractionStatusLabels: Record<KnowledgeGraphExtractionStatus, string> = {
  pending: '等待中',
  running: '抽取中',
  completed: '已完成',
  failed: '失败',
}

export const knowledgeGraphEntityTypeLabels: Record<KnowledgeGraphEntityType, string> = {
  character: '人物',
  setting: '设定',
  location: '地点',
  organization: '组织',
  item: '物品',
  event: '事件',
  clue: '线索',
  concept: '概念',
  custom: '自定义',
}

export const knowledgeGraphRelationTypeLabels: Record<KnowledgeGraphRelationType, string> = {
  relationship: '关系',
  conflict: '冲突',
  ally: '盟友',
  family: '亲属',
  belongs_to: '隶属',
  located_in: '位于',
  controls: '控制',
  causes: '导致',
  reveals: '揭示',
  foreshadows: '伏笔',
  setting_related: '设定',
  timeline_related: '时间线',
  custom: '自定义',
}

export const knowledgeGraphFactStatusLabels: Record<KnowledgeGraphFactStatus, string> = {
  confirmed: '确认',
  claimed: '声称',
  rumor: '传闻',
  hypothesis: '推测',
  dream: '梦境',
  plan: '计划',
  deprecated: '废弃',
}

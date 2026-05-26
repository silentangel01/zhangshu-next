export type SearchEntityType =
  | 'chapter'
  | 'setting'
  | 'character'
  | 'clue'
  | 'outline'
  | 'knowledge'
  | 'timeline'
  | 'graph'

export type SearchMode = 'fts5' | 'like'

export interface ProjectSearchResult {
  entity_type: SearchEntityType
  entity_id: string
  title: string
  subtitle: string | null
  matched_field: string | null
  snippet: string
  score: number
  updated_at: string | null
  metadata: Record<string, unknown> | null
}

export interface ProjectSearchResponse {
  query: string
  mode: SearchMode
  tokenizer: string
  total: number
  limit: number
  offset: number
  results: ProjectSearchResult[]
}

export interface RebuildSearchIndexResponse {
  project_id: string
  indexed_count: number
  message: string
}

export const SEARCH_ENTITY_TYPE_LABELS: Record<SearchEntityType, string> = {
  chapter: '正文',
  setting: '设定',
  character: '人物',
  clue: '伏笔',
  outline: '大纲',
  knowledge: '知识库',
  timeline: '时间线',
  graph: '关系图',
}

export const SEARCH_FILTER_OPTIONS: { value: SearchEntityType | 'all'; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'chapter', label: '正文' },
  { value: 'setting', label: '设定' },
  { value: 'character', label: '人物' },
  { value: 'clue', label: '伏笔' },
  { value: 'outline', label: '大纲' },
  { value: 'knowledge', label: '知识库' },
  { value: 'timeline', label: '时间线' },
  { value: 'graph', label: '关系图' },
]

export type SearchMatchedField = 'title' | 'content'

export interface ChapterSearchResult {
  chapter_id: string
  chapter_title: string
  volume_title: string | null
  matched_field: SearchMatchedField
  snippet: string
  updated_at: string
}

export interface ProjectSearchResponse {
  query: string
  results: ChapterSearchResult[]
}

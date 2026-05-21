export type ManuscriptExportScope = 'project' | 'volume' | 'chapter'
export type ManuscriptExportFormat = 'txt' | 'md' | 'docx'

export interface ManuscriptExportPayload {
  scope: ManuscriptExportScope
  volume_id?: string | null
  chapter_id?: string | null
  format: ManuscriptExportFormat
}

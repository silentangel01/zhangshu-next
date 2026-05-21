export type ImportType = 'legacy_json' | 'folder_zip' | 'external_files'

export interface ImportPreviewVolume {
  temp_id: string
  title: string
  order_index: number
  chapter_count: number
  chapters: string[]
}

export interface ImportPreviewReport {
  files_detected: string[]
  files_skipped: string[]
  encoding_issues: string[]
  empty_files: string[]
  duplicate_titles: string[]
  unsupported_files: string[]
}

export interface ImportPreview {
  import_id: string
  import_type: ImportType
  detected_project_title: string
  summary: string | null
  volume_count: number
  chapter_count: number
  total_word_count: number
  volumes: ImportPreviewVolume[]
  unassigned_chapter_count: number
  unassigned_chapters: string[]
  warnings: string[]
  unsupported_items: string[]
  failed_files: string[]
  report: ImportPreviewReport
  can_import: boolean
}

export interface ConfirmImportPayload {
  import_id?: string | null
  mode: 'create_project' | 'append_project'
  project_id?: string | null
  project_title?: string | null
}

export interface ImportReport {
  created_project_id: string
  created_volume_count: number
  created_chapter_count: number
  total_word_count: number
  warnings: string[]
  unsupported_items: string[]
  failed_files: string[]
  report_id: string
  report_path: string
}

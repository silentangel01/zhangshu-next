export type ImportType = 'legacy_json' | 'folder_zip'

export interface ImportPreviewVolume {
  temp_id: string
  title: string
  order_index: number
  chapter_count: number
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
  warnings: string[]
  unsupported_items: string[]
  failed_files: string[]
  can_import: boolean
}

export interface ConfirmImportPayload {
  mode: 'create_project'
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

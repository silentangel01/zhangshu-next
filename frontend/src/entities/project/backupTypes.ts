export interface RestoreCounts {
  volumes: number
  chapters: number
  materials: number
}

export interface RestoreReport {
  project_id: string
  project_title: string
  counts: RestoreCounts
  warnings: string[]
  errors: string[]
}

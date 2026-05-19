export interface Volume {
  id: string
  project_id: string
  title: string
  order_index: number
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface CreateVolumePayload {
  title: string
  order_index: number
}

export interface UpdateVolumePayload {
  title?: string
  order_index?: number
}

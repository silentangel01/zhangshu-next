import { apiRequest } from '@/shared/api/client'

import type {
  CreateSettingPayload,
  SettingFilters,
  SettingItem,
  UpdateSettingPayload,
} from './types'

function buildQuery(filters?: SettingFilters): string {
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

export function listProjectSettings(
  projectId: string,
  filters?: SettingFilters,
): Promise<SettingItem[]> {
  return apiRequest<SettingItem[]>(`/api/projects/${projectId}/settings${buildQuery(filters)}`)
}

export function createSetting(
  projectId: string,
  payload: CreateSettingPayload,
): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/api/projects/${projectId}/settings`, {
    method: 'POST',
    body: payload,
  })
}

export function getSetting(settingId: string): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/api/settings/${settingId}`)
}

export function updateSetting(
  settingId: string,
  payload: UpdateSettingPayload,
): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/api/settings/${settingId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteSetting(settingId: string): Promise<SettingItem | void> {
  return apiRequest<SettingItem | void>(`/api/settings/${settingId}`, {
    method: 'DELETE',
  })
}

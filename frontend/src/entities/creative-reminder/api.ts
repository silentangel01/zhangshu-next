import { apiRequest } from '@/shared/api/client'

import type { CreativeReminderFilters, CreativeReminderList } from './types'

function buildQuery(filters?: CreativeReminderFilters) {
  if (!filters) {
    return ''
  }
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value)
    }
  })
  const query = params.toString()
  return query ? `?${query}` : ''
}

export function listCreativeReminders(
  projectId: string,
  filters?: CreativeReminderFilters,
): Promise<CreativeReminderList> {
  return apiRequest<CreativeReminderList>(
    `/api/projects/${projectId}/creative-reminders${buildQuery(filters)}`,
  )
}

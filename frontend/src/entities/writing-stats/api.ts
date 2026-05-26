import { apiRequest } from '@/shared/api/client'
import type { RangeDays, WritingStatsOverview } from './types'

export function getWritingStatsOverview(
  projectId: string,
  days: RangeDays = 90,
): Promise<WritingStatsOverview> {
  return apiRequest<WritingStatsOverview>(
    `/api/projects/${projectId}/writing-stats/overview?days=${days}`,
  )
}

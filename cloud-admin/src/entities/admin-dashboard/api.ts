import { apiRequest } from '@/shared/api/client'
import type { ActivitySeries, DashboardSummary, FeedbackStats } from './types'

export function getDashboardSummary() {
  return apiRequest<DashboardSummary>('/api/admin/dashboard/summary')
}

export function getActivitySeries(days = 14) {
  return apiRequest<ActivitySeries>(`/api/admin/dashboard/activity?days=${days}`)
}

export function getFeedbackStats() {
  return apiRequest<FeedbackStats>('/api/admin/dashboard/feedback-stats')
}

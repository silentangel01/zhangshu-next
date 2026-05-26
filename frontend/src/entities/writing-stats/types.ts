export interface WritingStatsDailyPoint {
  date: string
  net_words: number
  added_words: number
  deleted_words: number
  event_count: number
  active_minutes_estimated: number
}

export interface WritingStatsHourlyPoint {
  hour: number
  net_words: number
  event_count: number
}

export interface WritingStatsVolumeBreakdownItem {
  volume_id: string | null
  title: string
  total_words: number
  chapter_count: number
}

export interface WritingStatsChapterRankingItem {
  chapter_id: string
  title: string
  volume_id: string | null
  volume_title: string
  total_words: number
  delta_words_7d: number
  updated_at: string
}

export interface WritingStatsOverview {
  project_id: string
  generated_at: string
  range_days: number
  total_words: number
  target_words: number | null
  progress_percent: number | null
  today_net_words: number
  week_net_words: number
  month_net_words: number
  current_streak_days: number
  longest_streak_days: number
  average_daily_words_30d: number
  estimated_today_minutes: number
  estimated_words_per_hour_today: number
  daily: WritingStatsDailyPoint[]
  hourly: WritingStatsHourlyPoint[]
  volume_breakdown: WritingStatsVolumeBreakdownItem[]
  chapter_rankings: WritingStatsChapterRankingItem[]
  warnings: string[]
}

export type RangeDays = 30 | 90 | 365

<script setup lang="ts">
import type { WritingStatsOverview } from '@/entities/writing-stats/types'
import { formatMinutes, formatNumber, formatSignedWords } from './statsFormatters'

defineProps<{ overview: WritingStatsOverview }>()
</script>

<template>
  <div class="metric-strip">
    <div class="metric">
      <span class="metric-label">总字数</span>
      <span class="metric-value">{{ formatNumber(overview.total_words) }}</span>
    </div>
    <div class="metric accent">
      <span class="metric-label">今日净增</span>
      <span class="metric-value" :class="overview.today_net_words < 0 ? 'negative' : ''">
        {{ formatSignedWords(overview.today_net_words) }}
      </span>
    </div>
    <div class="metric">
      <span class="metric-label">本周净增</span>
      <span class="metric-value" :class="overview.week_net_words < 0 ? 'negative' : ''">
        {{ formatSignedWords(overview.week_net_words) }}
      </span>
    </div>
    <div class="metric">
      <span class="metric-label">本月净增</span>
      <span class="metric-value" :class="overview.month_net_words < 0 ? 'negative' : ''">
        {{ formatSignedWords(overview.month_net_words) }}
      </span>
    </div>
    <div class="metric">
      <span class="metric-label">连续写作</span>
      <span class="metric-value">{{ overview.current_streak_days }} 天</span>
    </div>
    <div class="metric">
      <span class="metric-label">今日活跃（估算）</span>
      <span class="metric-value">{{ formatMinutes(overview.estimated_today_minutes) }}</span>
    </div>
    <div class="metric">
      <span class="metric-label">近 30 日日均</span>
      <span class="metric-value">{{ formatNumber(Math.round(overview.average_daily_words_30d)) }}</span>
    </div>
  </div>
</template>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: var(--zs-space-3);
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-surface);
}

.metric.accent {
  border-color: var(--zs-module-stats);
  background: color-mix(in srgb, var(--zs-module-stats) 6%, var(--zs-color-surface));
}

.metric-label {
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.metric-value {
  color: var(--zs-color-text);
  font-size: 1.15rem;
  font-weight: 800;
  line-height: 1.2;
}

.metric-value.negative {
  color: var(--zs-color-warning);
}
</style>

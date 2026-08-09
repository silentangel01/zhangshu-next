<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { getWritingStatsOverview } from '@/entities/writing-stats/api'
import type { RangeDays, WritingStatsOverview } from '@/entities/writing-stats/types'
import ChapterRankingTable from '@/features/stats/ChapterRankingTable.vue'
import DailyWordsChart from '@/features/stats/DailyWordsChart.vue'
import HourlyActivityChart from '@/features/stats/HourlyActivityChart.vue'
import StatsMetricStrip from '@/features/stats/StatsMetricStrip.vue'
import VolumeBreakdown from '@/features/stats/VolumeBreakdown.vue'
import WritingHeatmap from '@/features/stats/WritingHeatmap.vue'
import { formatNumber, formatPercent, formatSignedWords } from '@/features/stats/statsFormatters'

const route = useRoute()

const overview = ref<WritingStatsOverview | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')
const rangeDays = ref<RangeDays>(90)

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const RANGE_OPTIONS: { label: string; value: RangeDays }[] = [
  { label: '30 天', value: 30 },
  { label: '90 天', value: 90 },
  { label: '全年', value: 365 },
]

onMounted(() => {
  void loadOverview()
})

watch([projectId, rangeDays], () => {
  void loadOverview()
})

async function loadOverview() {
  if (!projectId.value) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    overview.value = await getWritingStatsOverview(projectId.value, rangeDays.value)
  } catch (error) {
    void error
    errorMessage.value = '加载写作统计失败，请检查项目是否存在。'
    overview.value = null
  } finally {
    isLoading.value = false
  }
}

async function handleRefresh() {
  await loadOverview()
}

function setRange(value: RangeDays) {
  rangeDays.value = value
}

const hasEvents = computed(() => {
  if (!overview.value) {
    return false
  }

  return overview.value.daily.some((d) => d.event_count > 0)
})
</script>

<template>
  <main class="stats-page">
    <header class="stats-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <h1>写作统计</h1>
      </div>
      <div class="header-controls">
        <div class="range-control">
          <button
            v-for="opt in RANGE_OPTIONS"
            :key="opt.value"
            type="button"
            class="range-btn"
            :class="{ active: rangeDays === opt.value }"
            @click="setRange(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
        <button type="button" class="refresh-btn" :disabled="isLoading" @click="handleRefresh">
          刷新
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="isLoading && !overview" class="state-message">正在加载统计数据……</section>

    <template v-if="overview">
      <section class="stats-section">
        <StatsMetricStrip :overview="overview" />
      </section>

      <section v-if="overview.target_words" class="stats-section">
        <h2 class="section-title">目标进度</h2>
        <div class="progress-row">
          <div class="progress-bar-track">
            <div
              class="progress-bar-fill"
              :style="{ width: `${overview.progress_percent ?? 0}%` }"
            />
          </div>
          <span class="progress-text">
            {{ formatNumber(overview.total_words) }} /
            {{ formatNumber(overview.target_words) }} （{{
              formatPercent(overview.progress_percent)
            }}）
          </span>
        </div>
      </section>
      <section v-else class="stats-section">
        <p class="hint-text">未设置目标字数，可在项目设置中配置。</p>
      </section>

      <section v-if="overview.warnings.length > 0" class="stats-section">
        <div class="warning-box">
          <p v-for="(warning, i) in overview.warnings" :key="i">{{ warning }}</p>
        </div>
      </section>

      <section class="stats-section">
        <h2 class="section-title">写作日历</h2>
        <WritingHeatmap v-if="hasEvents" :daily="overview.daily" />
        <p v-else class="empty-hint">写作趋势从现在开始记录，修改并保存章节正文后即可看到数据。</p>
      </section>

      <section class="stats-section">
        <h2 class="section-title">每日净增</h2>
        <DailyWordsChart :daily="overview.daily" />
      </section>

      <div class="two-col">
        <section class="stats-section">
          <h2 class="section-title">小时分布</h2>
          <HourlyActivityChart :hourly="overview.hourly" />
        </section>

        <section class="stats-section">
          <h2 class="section-title">分卷字数</h2>
          <VolumeBreakdown :items="overview.volume_breakdown" />
        </section>
      </div>

      <section class="stats-section">
        <h2 class="section-title">章节增长排行（近 7 天）</h2>
        <ChapterRankingTable :rankings="overview.chapter_rankings" />
      </section>

      <section v-if="hasEvents" class="stats-section debug-info">
        <details>
          <summary>高级信息</summary>
          <p>今日新增 {{ formatSignedWords(overview.today_net_words) }} 字</p>
          <p v-if="overview.estimated_words_per_hour_today > 0">
            今日速度约 {{ Math.round(overview.estimated_words_per_hour_today) }} 字/小时
          </p>
          <p>最长连续 {{ overview.longest_streak_days }} 天</p>
        </details>
      </section>
    </template>
  </main>
</template>

<style scoped>
.stats-page {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--zs-space-6);
  box-sizing: border-box;
  min-height: 100vh;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.stats-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-5);
  flex-wrap: wrap;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.back-link {
  display: inline-block;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
  font-weight: 800;
  font-size: 0.85rem;
  text-decoration: none;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
  flex-wrap: wrap;
}

.range-control {
  display: flex;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
}

.range-btn {
  border: none;
  border-right: 1px solid var(--zs-color-border);
  padding: 6px 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  min-height: auto;
  border-radius: 0;
}

.range-btn:last-child {
  border-right: none;
}

.range-btn.active {
  background: var(--zs-module-stats);
  color: white;
}

.refresh-btn {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 6px 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  min-height: auto;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-banner {
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-weight: 700;
  margin-bottom: var(--zs-space-4);
}

.state-message {
  display: grid;
  place-items: center;
  min-height: 200px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  color: var(--zs-color-text-muted);
}

.stats-section {
  margin-bottom: var(--zs-space-5);
}

.section-title {
  margin: 0 0 var(--zs-space-3);
  font-size: 0.92rem;
  font-weight: 800;
  color: var(--zs-color-text);
}

.progress-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
}

.progress-bar-track {
  flex: 1;
  height: 14px;
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface-soft);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: var(--zs-radius-sm);
  background: var(--zs-module-stats);
  transition: width 400ms ease;
}

.progress-text {
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--zs-color-text-muted);
}

.hint-text {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.warning-box {
  border: 1px solid var(--zs-color-warning);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3);
  background: color-mix(in srgb, var(--zs-color-warning) 8%, var(--zs-color-surface));
}

.warning-box p {
  margin: 0;
  color: var(--zs-color-warning);
  font-size: 0.85rem;
  font-weight: 700;
}

.empty-hint {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--zs-space-5);
}

.debug-info {
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-3);
}

.debug-info summary {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  cursor: pointer;
}

.debug-info p {
  margin: 4px 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

@media (max-width: 768px) {
  .stats-page {
    padding: var(--zs-space-4);
  }

  .two-col {
    grid-template-columns: 1fr;
  }

  .stats-header {
    flex-direction: column;
  }
}
</style>

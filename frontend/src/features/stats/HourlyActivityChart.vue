<script setup lang="ts">
import { computed } from 'vue'
import type { WritingStatsHourlyPoint } from '@/entities/writing-stats/types'

const props = defineProps<{ hourly: WritingStatsHourlyPoint[] }>()

interface HourBar {
  hour: number
  label: string
  heightPercent: number
  netWords: number
  tooltip: string
}

const bars = computed<HourBar[]>(() => {
  const points = props.hourly
  if (points.length === 0) {
    return []
  }

  const maxNet = Math.max(1, ...points.map((p) => Math.abs(p.net_words)))

  return points.map((point) => {
    const heightPercent = Math.max(2, (Math.abs(point.net_words) / maxNet) * 100)
    const label = `${String(point.hour).padStart(2, '0')}时`
    const tooltip = `${label}：净增 ${point.net_words.toLocaleString()} 字（${point.event_count} 次保存）`
    return {
      hour: point.hour,
      label,
      heightPercent: point.net_words === 0 ? 0 : heightPercent,
      netWords: point.net_words,
      tooltip,
    }
  })
})

const hasData = computed(() => props.hourly.some((p) => p.event_count > 0))
</script>

<template>
  <div class="hourly-chart">
    <div v-if="!hasData" class="empty-state">暂无小时分布数据</div>
    <div v-else class="chart-body">
      <div class="bars-row">
        <div
          v-for="bar in bars"
          :key="bar.hour"
          class="hour-col"
          :title="bar.tooltip"
        >
          <div class="bar-track">
            <div
              class="bar-fill"
              :style="{ height: `${bar.heightPercent}%` }"
            />
          </div>
          <span v-if="bar.hour % 3 === 0" class="hour-label">{{ bar.hour }}</span>
          <span v-else class="hour-label dot">·</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hourly-chart {
  width: 100%;
  min-height: 120px;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 120px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.chart-body {
  height: 130px;
}

.bars-row {
  display: flex;
  gap: 2px;
  height: 100%;
}

.hour-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.bar-track {
  flex: 1;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar-fill {
  width: 100%;
  border-radius: 2px 2px 0 0;
  background: var(--zs-module-stats);
  opacity: 0.6;
  min-height: 0;
  transition: height 200ms ease;
}

.hour-col:hover .bar-fill {
  opacity: 1;
}

.hour-label {
  color: var(--zs-color-text-muted);
  font-size: 0.62rem;
  line-height: 1;
  white-space: nowrap;
}

.hour-label.dot {
  opacity: 0.4;
}
</style>

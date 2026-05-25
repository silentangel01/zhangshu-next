<script setup lang="ts">
import { computed } from 'vue'
import type { WritingStatsDailyPoint } from '@/entities/writing-stats/types'
import { formatSignedWords } from './statsFormatters'

const props = defineProps<{ daily: WritingStatsDailyPoint[] }>()

interface BarData {
  date: string
  netWords: number
  heightPercent: number
  isNegative: boolean
  tooltip: string
}

const bars = computed<BarData[]>(() => {
  const points = props.daily
  if (points.length === 0) {
    return []
  }

  const maxAbs = Math.max(1, ...points.map((p) => Math.abs(p.net_words)))

  return points.map((point) => {
    const heightPercent = Math.max(2, (Math.abs(point.net_words) / maxAbs) * 100)
    const shortDate = point.date.slice(5)
    const tooltip = `${point.date}：${formatSignedWords(point.net_words)}`
    return {
      date: shortDate,
      netWords: point.net_words,
      heightPercent,
      isNegative: point.net_words < 0,
      tooltip,
    }
  })
})

const hasData = computed(() => props.daily.some((p) => p.net_words !== 0))
</script>

<template>
  <div class="daily-chart">
    <div v-if="!hasData" class="empty-state">暂无每日净增数据</div>
    <div v-else class="bar-container">
      <div class="bars">
        <div
          v-for="(bar, i) in bars"
          :key="i"
          class="bar-wrapper"
          :title="bar.tooltip"
        >
          <div class="bar-space">
            <div
              class="bar"
              :class="{ negative: bar.isNegative, positive: !bar.isNegative && bar.netWords > 0 }"
              :style="{ height: `${bar.heightPercent}%` }"
            />
          </div>
        </div>
      </div>
      <div class="baseline" />
    </div>
  </div>
</template>

<style scoped>
.daily-chart {
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

.bar-container {
  position: relative;
  height: 140px;
}

.bars {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 100%;
}

.bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  height: 100%;
  min-width: 0;
}

.bar-space {
  display: flex;
  align-items: flex-end;
  height: 100%;
}

.bar {
  width: 100%;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  transition: height 200ms ease;
}

.bar.positive {
  background: var(--zs-module-stats);
  opacity: 0.7;
}

.bar.negative {
  background: var(--zs-color-warning);
  opacity: 0.6;
  border-radius: 0 0 2px 2px;
  align-self: flex-start;
}

.bar-wrapper:hover .bar.positive {
  opacity: 1;
}

.bar-wrapper:hover .bar.negative {
  opacity: 1;
}

.baseline {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--zs-color-border);
}
</style>

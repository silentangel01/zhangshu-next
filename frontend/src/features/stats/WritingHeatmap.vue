<script setup lang="ts">
import { computed } from 'vue'
import type { WritingStatsDailyPoint } from '@/entities/writing-stats/types'
import { formatSignedWords, getHeatmapLevel } from './statsFormatters'

const props = defineProps<{ daily: WritingStatsDailyPoint[] }>()

interface HeatmapCell {
  date: string
  level: 0 | 1 | 2 | 3 | 4
  netWords: number
  addedWords: number
  deletedWords: number
  tooltip: string
}

const cells = computed<HeatmapCell[]>(() => {
  return props.daily.map((point) => {
    const level = getHeatmapLevel(point.net_words)
    const tooltip =
      `${point.date}：净增 ${formatSignedWords(point.net_words)}` +
      `\n新增 ${point.added_words.toLocaleString()}，删除 ${point.deleted_words.toLocaleString()}`
    return {
      date: point.date,
      level,
      netWords: point.net_words,
      addedWords: point.added_words,
      deletedWords: point.deleted_words,
      tooltip,
    }
  })
})

const weeks = computed<HeatmapCell[][]>(() => {
  const result: HeatmapCell[][] = []
  const allCells = cells.value

  if (allCells.length === 0) {
    return []
  }

  const firstCell = allCells[0]
  if (!firstCell) {
    return []
  }

  const firstDate = new Date(firstCell.date)
  const firstDayOfWeek = firstDate.getDay()

  let currentWeek: HeatmapCell[] = []
  for (let i = 0; i < firstDayOfWeek; i++) {
    currentWeek.push({ date: '', level: 0, netWords: 0, addedWords: 0, deletedWords: 0, tooltip: '' })
  }

  for (const cell of allCells) {
    currentWeek.push(cell)
    if (currentWeek.length === 7) {
      result.push(currentWeek)
      currentWeek = []
    }
  }

  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) {
      currentWeek.push({ date: '', level: 0, netWords: 0, addedWords: 0, deletedWords: 0, tooltip: '' })
    }
    result.push(currentWeek)
  }

  return result
})

const monthLabels = computed<{ label: string; col: number }[]>(() => {
  const labels: { label: string; col: number }[] = []
  const allCells = cells.value
  if (allCells.length === 0) {
    return labels
  }

  let lastMonth = ''
  for (let i = 0; i < allCells.length; i++) {
    const cell = allCells[i]
    if (!cell) {
      continue
    }

    const date = new Date(cell.date)
    const monthKey = `${date.getFullYear()}-${date.getMonth()}`
    if (monthKey !== lastMonth) {
      const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
      const label = monthNames[date.getMonth()] ?? ''
      labels.push({ label, col: Math.floor(i / 7) })
      lastMonth = monthKey
    }
  }

  return labels
})
</script>

<template>
  <div class="heatmap-wrapper">
    <div v-if="monthLabels.length > 0" class="heatmap-months">
      <span
        v-for="ml in monthLabels"
        :key="ml.col"
        class="month-label"
        :style="{ gridColumn: ml.col + 1 }"
      >
        {{ ml.label }}
      </span>
    </div>

    <div class="heatmap-grid" :style="{ gridTemplateColumns: `repeat(${weeks.length}, 1fr)` }">
      <template v-for="(week, wi) in weeks" :key="wi">
        <div
          v-for="(cell, ci) in week"
          :key="`${wi}-${ci}`"
          class="heatmap-cell"
          :class="[`level-${cell.level}`, { empty: !cell.date }]"
          :title="cell.tooltip"
        />
      </template>
    </div>

    <div class="heatmap-legend">
      <span class="legend-label">少</span>
      <span class="legend-cell level-0" />
      <span class="legend-cell level-1" />
      <span class="legend-cell level-2" />
      <span class="legend-cell level-3" />
      <span class="legend-cell level-4" />
      <span class="legend-label">多</span>
    </div>
  </div>
</template>

<style scoped>
.heatmap-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.heatmap-months {
  display: grid;
  gap: 3px;
  padding-left: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.7rem;
}

.month-label {
  white-space: nowrap;
}

.heatmap-grid {
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
}

.heatmap-cell {
  aspect-ratio: 1;
  min-width: 10px;
  max-width: 16px;
  border-radius: 2px;
}

.heatmap-cell.empty {
  background: transparent;
}

.heatmap-cell.level-0 {
  background: var(--zs-heatmap-0);
}

.heatmap-cell.level-1 {
  background: var(--zs-heatmap-1);
}

.heatmap-cell.level-2 {
  background: var(--zs-heatmap-2);
}

.heatmap-cell.level-3 {
  background: var(--zs-heatmap-3);
}

.heatmap-cell.level-4 {
  background: var(--zs-heatmap-4);
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-end;
  color: var(--zs-color-text-muted);
  font-size: 0.7rem;
}

.legend-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>

<script setup lang="ts">
import { computed } from 'vue'
import type { WritingStatsVolumeBreakdownItem } from '@/entities/writing-stats/types'
import { formatNumber } from './statsFormatters'

const props = defineProps<{ items: WritingStatsVolumeBreakdownItem[] }>()

const totalWords = computed(() => props.items.reduce((sum, item) => sum + item.total_words, 0))

interface VolumeBar extends WritingStatsVolumeBreakdownItem {
  widthPercent: number
}

const bars = computed<VolumeBar[]>(() => {
  const total = totalWords.value || 1
  return props.items.map((item) => ({
    ...item,
    widthPercent: Math.max(2, (item.total_words / total) * 100),
  }))
})
</script>

<template>
  <div class="volume-breakdown">
    <div v-if="items.length === 0" class="empty-state">暂无分卷数据</div>
    <template v-else>
      <div class="volume-bar-row">
        <div
          v-for="item in bars"
          :key="item.volume_id ?? 'unassigned'"
          class="volume-segment"
          :style="{ width: `${item.widthPercent}%` }"
          :title="`${item.title}：${formatNumber(item.total_words)} 字（${item.chapter_count} 章）`"
        />
      </div>
      <div class="volume-list">
        <div v-for="item in items" :key="item.volume_id ?? 'unassigned'" class="volume-row">
          <span class="volume-title">{{ item.title }}</span>
          <span class="volume-words">{{ formatNumber(item.total_words) }} 字</span>
          <span class="volume-chapters">{{ item.chapter_count }} 章</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.volume-breakdown {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 60px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.volume-bar-row {
  display: flex;
  height: 12px;
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
  background: var(--zs-color-surface-soft);
}

.volume-segment {
  min-width: 4px;
  background: var(--zs-module-stats);
  opacity: 0.7;
}

.volume-segment:nth-child(2n) {
  opacity: 0.5;
}

.volume-segment:nth-child(3n) {
  opacity: 0.85;
}

.volume-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.volume-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
  font-size: 0.85rem;
}

.volume-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
}

.volume-words {
  white-space: nowrap;
  color: var(--zs-color-text);
  font-weight: 800;
}

.volume-chapters {
  white-space: nowrap;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}
</style>

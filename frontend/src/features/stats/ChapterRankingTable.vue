<script setup lang="ts">
import type { WritingStatsChapterRankingItem } from '@/entities/writing-stats/types'
import { formatNumber, formatSignedWords } from './statsFormatters'
import { formatDateTime } from '@/shared/utils/formatDateTime'

defineProps<{ rankings: WritingStatsChapterRankingItem[] }>()
</script>

<template>
  <div class="ranking-table-wrapper">
    <div v-if="rankings.length === 0" class="empty-state">暂无章节增长数据</div>
    <table v-else class="ranking-table">
      <thead>
        <tr>
          <th>章节</th>
          <th>分卷</th>
          <th class="num">当前字数</th>
          <th class="num">近 7 天</th>
          <th class="num">更新时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in rankings" :key="item.chapter_id">
          <td class="title-cell">{{ item.title }}</td>
          <td class="volume-cell">{{ item.volume_title }}</td>
          <td class="num">{{ formatNumber(item.total_words) }}</td>
          <td class="num" :class="item.delta_words_7d < 0 ? 'negative' : item.delta_words_7d > 0 ? 'positive' : ''">
            {{ formatSignedWords(item.delta_words_7d) }}
          </td>
          <td class="num muted">{{ formatDateTime(item.updated_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.ranking-table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 80px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.ranking-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.ranking-table th {
  padding: 8px 10px;
  border-bottom: 1px solid var(--zs-color-border);
  color: var(--zs-color-text-muted);
  font-weight: 700;
  font-size: 0.75rem;
  text-align: left;
  white-space: nowrap;
}

.ranking-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--zs-color-border-soft);
  vertical-align: middle;
}

.ranking-table tr:last-child td {
  border-bottom: none;
}

.title-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
}

.volume-cell {
  color: var(--zs-color-text-muted);
  white-space: nowrap;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.num.muted {
  color: var(--zs-color-text-muted);
}

.positive {
  color: var(--zs-module-stats);
}

.negative {
  color: var(--zs-color-warning);
}
</style>

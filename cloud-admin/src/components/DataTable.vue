<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  columns: { key: string; label: string; width?: string }[]
  rows: Record<string, unknown>[]
  emptyText?: string
  total?: number
  page?: number
  pageSize?: number
}>()

const emit = defineEmits<{
  'update:page': [page: number]
}>()

const totalPages = computed(() => {
  if (!props.total || !props.pageSize) return 1
  return Math.max(1, Math.ceil(props.total / props.pageSize))
})
</script>

<template>
  <div class="data-table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="col.width ? { width: col.width } : {}">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td :colspan="columns.length" class="empty-cell">{{ emptyText ?? '暂无数据' }}</td>
        </tr>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="col in columns" :key="col.key">
            <slot :name="col.key" :row="row" :value="row[col.key]">
              {{ row[col.key] ?? '-' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="total !== undefined && totalPages > 1" class="pagination">
      <button
        class="btn btn-sm"
        :disabled="!page || page <= 1"
        @click="emit('update:page', (page ?? 1) - 1)"
      >
        &larr; 上一页
      </button>
      <span class="page-info">
        第 {{ page ?? 1 }} / {{ totalPages }} 页（共 {{ total }} 条）
      </span>
      <button
        class="btn btn-sm"
        :disabled="!page || page >= totalPages"
        @click="emit('update:page', (page ?? 1) + 1)"
      >
        下一页 &rarr;
      </button>
    </div>
  </div>
</template>

<style scoped>
.data-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--ca-border);
  border-radius: var(--ca-radius);
  background: var(--ca-surface);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: var(--ca-space-3) var(--ca-space-4);
  background: var(--ca-bg);
  color: var(--ca-text-muted);
  font-weight: 500;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--ca-border);
  white-space: nowrap;
}
.data-table td {
  padding: var(--ca-space-3) var(--ca-space-4);
  border-bottom: 1px solid var(--ca-border);
  vertical-align: middle;
}
.data-table tr:last-child td {
  border-bottom: none;
}
.data-table tr:hover td {
  background: #fafbfc;
}
.empty-cell {
  text-align: center;
  color: var(--ca-text-muted);
  padding: var(--ca-space-6) !important;
}
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ca-space-3) var(--ca-space-4);
  border-top: 1px solid var(--ca-border);
}
.page-info {
  font-size: 13px;
  color: var(--ca-text-muted);
}
</style>

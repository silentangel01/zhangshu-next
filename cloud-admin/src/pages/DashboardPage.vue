<script setup lang="ts">
import { onMounted, ref } from 'vue'
import StatTile from '@/components/StatTile.vue'
import { getDashboardSummary, getActivitySeries } from '@/entities/admin-dashboard/api'
import type { DashboardSummary, ActivitySeries } from '@/entities/admin-dashboard/types'

const summary = ref<DashboardSummary | null>(null)
const activity = ref<ActivitySeries | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const [s, a] = await Promise.all([getDashboardSummary(), getActivitySeries(14)])
    summary.value = s
    activity.value = a
  } catch {
    /* handled by 401 redirect */
  } finally {
    loading.value = false
  }
})

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
</script>

<template>
  <div>
    <h2 class="page-title">概览</h2>
    <p v-if="loading" class="loading-text">加载中...</p>
    <template v-else-if="summary">
      <div class="stat-grid">
        <StatTile label="总用户" :value="summary.total_users" />
        <StatTile label="今日新增" :value="summary.today_registrations" />
        <StatTile label="24h 活跃" :value="summary.active_24h" />
        <StatTile label="7d 活跃" :value="summary.active_7d" />
        <StatTile label="待处理反馈" :value="summary.open_feedback" />
        <StatTile label="紧急反馈" :value="summary.urgent_feedback" />
        <StatTile label="云项目" :value="summary.total_cloud_projects" />
        <StatTile label="总存储" :value="formatBytes(summary.total_storage_bytes)" />
      </div>
      <div v-if="activity" class="card activity-section">
        <h3>近 14 天活动趋势</h3>
        <table class="trend-table">
          <thead>
            <tr><th>日期</th><th>活跃</th><th>注册</th><th>反馈</th><th>备份</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in activity.daily_active" :key="row.day">
              <td>{{ row.day }}</td>
              <td>{{ row.count }}</td>
              <td>{{ activity.daily_registrations.find(r => r.day === row.day)?.count ?? 0 }}</td>
              <td>{{ activity.daily_feedback.find(r => r.day === row.day)?.count ?? 0 }}</td>
              <td>{{ activity.daily_backups.find(r => r.day === row.day)?.count ?? 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-title { font-size: 18px; font-weight: 600; margin-bottom: var(--ca-space-5); }
.loading-text { color: var(--ca-text-muted); }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--ca-space-4); margin-bottom: var(--ca-space-6); }
.activity-section { margin-top: var(--ca-space-4); }
.activity-section h3 { font-size: 15px; margin-bottom: var(--ca-space-4); }
.trend-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.trend-table th, .trend-table td { padding: var(--ca-space-2) var(--ca-space-3); text-align: right; border-bottom: 1px solid var(--ca-border); }
.trend-table th { color: var(--ca-text-muted); font-weight: 500; font-size: 12px; }
.trend-table td:first-child, .trend-table th:first-child { text-align: left; }
</style>

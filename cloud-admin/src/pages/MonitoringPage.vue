<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getMonitoringOverview, refreshMonitoring } from '@/entities/admin-monitoring/api'
import type { MonitoringOverview } from '@/entities/admin-monitoring/types'
import { listAuditLogs } from '@/entities/admin-audit/api'
import type { AuditLogEntry } from '@/entities/admin-audit/types'
import { useToast } from '@/shared/composables/useToast'

const toast = useToast()
const overview = ref<MonitoringOverview | null>(null)
const loading = ref(true)
const refreshing = ref<Record<string, boolean>>({})

// Audit log state
const auditLogs = ref<AuditLogEntry[]>([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = 20
const auditLoading = ref(false)

onMounted(() => {
  load()
  loadAuditLogs()
})

async function load() {
  loading.value = true
  try {
    overview.value = await getMonitoringOverview()
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '加载监控数据失败')
  } finally {
    loading.value = false
  }
}

async function refreshModule(module: string) {
  refreshing.value = { ...refreshing.value, [module]: true }
  try {
    overview.value = await refreshMonitoring(module)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '刷新失败')
  } finally {
    refreshing.value = { ...refreshing.value, [module]: false }
  }
}

async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const res = await listAuditLogs({
      limit: auditPageSize,
      offset: (auditPage.value - 1) * auditPageSize,
    })
    auditLogs.value = res.items
    auditTotal.value = res.total
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '加载审计日志失败')
  } finally {
    auditLoading.value = false
  }
}

function onAuditPageChange(p: number) {
  auditPage.value = p
  loadAuditLogs()
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatBps(bps: number): string {
  if (bps < 1024) return `${bps.toFixed(0)} bit/s`
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} Kbit/s`
  return `${(bps / (1024 * 1024)).toFixed(2)} Mbit/s`
}

function formatCachedAt(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

function formatAuditTime(iso: string | null): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'medium' })
  } catch {
    return iso
  }
}

function resultBadge(result: string): string {
  if (result === 'success') return 'badge-success'
  if (result === 'failure') return 'badge-warning'
  return 'badge-danger'
}

function daysUntil(iso: string): number | null {
  if (!iso) return null
  try {
    const exp = new Date(iso).getTime()
    const now = Date.now()
    return Math.ceil((exp - now) / (1000 * 60 * 60 * 24))
  } catch {
    return null
  }
}

function pctClass(pct: number): string {
  if (pct >= 90) return 'bar-danger'
  if (pct >= 70) return 'bar-warning'
  return 'bar-ok'
}

const serverExpiredDays = computed(() => {
  const info = overview.value?.server.data?.info
  return info ? daysUntil(info.expired_at) : null
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">运维监控</h2>
      <button class="btn" :disabled="loading" @click="load">刷新全部</button>
    </div>

    <p v-if="loading" class="loading-text">加载中...</p>

    <template v-else-if="overview">
      <div class="monitor-grid">
        <!-- ── 账户余额 ─────────────────────── -->
        <section class="card monitor-card">
          <div class="card-header">
            <h3>账户余额</h3>
            <div class="card-actions">
              <span class="cache-time">{{ formatCachedAt(overview.billing.cached_at) }}</span>
              <button
                class="btn-icon"
                title="刷新"
                :disabled="refreshing.billing"
                @click="refreshModule('billing')"
              >&#8635;</button>
            </div>
          </div>

          <div v-if="overview.billing.error" class="card-error">
            <p>{{ overview.billing.error }}</p>
            <button class="btn btn-sm" @click="refreshModule('billing')">重试</button>
          </div>

          <div v-else-if="overview.billing.data" class="billing-body">
            <div class="billing-main">
              <span class="billing-amount">{{ overview.billing.data.available_amount }}</span>
              <span class="billing-currency">{{ overview.billing.data.currency }}</span>
            </div>
            <div class="billing-details">
              <div class="detail-row">
                <span class="detail-label">信用额度</span>
                <span class="detail-value">{{ overview.billing.data.credit_amount }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">网商银行</span>
                <span class="detail-value">{{ overview.billing.data.mybank_credit_amount }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">现金余额</span>
                <span class="detail-value">{{ overview.billing.data.available_cash_amount }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- ── OSS 存储 ─────────────────────── -->
        <section class="card monitor-card">
          <div class="card-header">
            <h3>OSS 存储</h3>
            <div class="card-actions">
              <span class="cache-time">{{ formatCachedAt(overview.oss.cached_at) }}</span>
              <button
                class="btn-icon"
                title="刷新"
                :disabled="refreshing.oss"
                @click="refreshModule('oss')"
              >&#8635;</button>
            </div>
          </div>

          <div v-if="overview.oss.error" class="card-error">
            <p>{{ overview.oss.error }}</p>
            <button class="btn btn-sm" @click="refreshModule('oss')">重试</button>
          </div>

          <div v-else-if="overview.oss.data" class="oss-body">
            <div class="oss-main">
              <div class="oss-stat-big">
                <span class="stat-number">{{ formatBytes(overview.oss.data.storage_bytes) }}</span>
                <span class="stat-label">总存储</span>
              </div>
              <div class="oss-stat-big">
                <span class="stat-number">{{ overview.oss.data.object_count.toLocaleString() }}</span>
                <span class="stat-label">对象数</span>
              </div>
            </div>
            <div class="oss-breakdown">
              <div class="detail-row">
                <span class="detail-label">标准存储</span>
                <span class="detail-value">{{ formatBytes(overview.oss.data.standard_storage) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">低频存储</span>
                <span class="detail-value">{{ formatBytes(overview.oss.data.ia_storage) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">归档存储</span>
                <span class="detail-value">{{ formatBytes(overview.oss.data.archive_storage) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Bucket</span>
                <span class="detail-value">{{ overview.oss.data.bucket_name }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- ── 服务器信息 ─────────────────────── -->
        <section class="card monitor-card">
          <div class="card-header">
            <h3>服务器状态</h3>
            <div class="card-actions">
              <span class="cache-time">{{ formatCachedAt(overview.server.cached_at) }}</span>
              <button
                class="btn-icon"
                title="刷新"
                :disabled="refreshing.server"
                @click="refreshModule('server')"
              >&#8635;</button>
            </div>
          </div>

          <div v-if="overview.server.error" class="card-error">
            <p>{{ overview.server.error }}</p>
            <button class="btn btn-sm" @click="refreshModule('server')">重试</button>
          </div>

          <div v-else-if="overview.server.data" class="server-body">
            <div class="server-top">
              <span
                class="badge"
                :class="overview.server.data.info.status === 'Running' ? 'badge-success' : 'badge-danger'"
              >{{ overview.server.data.info.status }}</span>
              <span class="server-name">{{ overview.server.data.info.name || overview.server.data.info.public_ip }}</span>
            </div>

            <div class="server-details">
              <div class="detail-row">
                <span class="detail-label">公网 IP</span>
                <span class="detail-value mono">{{ overview.server.data.info.public_ip }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">规格</span>
                <span class="detail-value">{{ overview.server.data.info.spec }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">系统</span>
                <span class="detail-value">{{ overview.server.data.info.os_name }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">到期时间</span>
                <span class="detail-value" :class="{ 'text-danger': serverExpiredDays !== null && serverExpiredDays <= 7 }">
                  {{ overview.server.data.info.expired_at
                    ? `${overview.server.data.info.expired_at.slice(0, 10)}`
                    : '-' }}
                  <template v-if="serverExpiredDays !== null">
                    <span v-if="serverExpiredDays <= 0" class="badge badge-danger">已过期</span>
                    <span v-else-if="serverExpiredDays <= 7" class="badge badge-warning">{{ serverExpiredDays }} 天后到期</span>
                    <span v-else class="text-muted">({{ serverExpiredDays }} 天)</span>
                  </template>
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- ── 服务器监控 ─────────────────────── -->
        <section class="card monitor-card monitor-card-wide">
          <div class="card-header">
            <h3>资源监控</h3>
          </div>

          <div v-if="overview.server.data" class="monitor-body">
            <div v-if="!overview.server.data.monitor.available" class="monitor-unavailable">
              <p>监控数据暂不可用</p>
              <p class="monitor-hint">新创建的服务器可能需要几分钟才能生成监控数据。</p>
            </div>
            <template v-else>
              <div class="metric-group">
                <div class="metric-row">
                  <span class="metric-label">CPU</span>
                  <div class="metric-bar-wrap">
                    <div
                      class="metric-bar"
                      :class="pctClass(overview.server.data.monitor.cpu_usage)"
                      :style="{ width: Math.min(overview.server.data.monitor.cpu_usage, 100) + '%' }"
                    />
                  </div>
                  <span class="metric-value">{{ overview.server.data.monitor.cpu_usage.toFixed(1) }}%</span>
                </div>

                <div class="metric-row">
                  <span class="metric-label">内存</span>
                  <div class="metric-bar-wrap">
                    <div
                      class="metric-bar"
                      :class="pctClass(overview.server.data.monitor.memory_usage)"
                      :style="{ width: Math.min(overview.server.data.monitor.memory_usage, 100) + '%' }"
                    />
                  </div>
                  <span class="metric-value">{{ overview.server.data.monitor.memory_usage.toFixed(1) }}%</span>
                </div>
              </div>

              <div class="io-grid">
                <div class="io-item">
                  <span class="io-label">磁盘读</span>
                  <span class="io-value">{{ overview.server.data.monitor.disk_read_iops.toFixed(0) }} IOPS</span>
                </div>
                <div class="io-item">
                  <span class="io-label">磁盘写</span>
                  <span class="io-value">{{ overview.server.data.monitor.disk_write_iops.toFixed(0) }} IOPS</span>
                </div>
                <div class="io-item">
                  <span class="io-label">入网</span>
                  <span class="io-value">{{ formatBps(overview.server.data.monitor.net_rx_bps) }}</span>
                </div>
                <div class="io-item">
                  <span class="io-label">出网</span>
                  <span class="io-value">{{ formatBps(overview.server.data.monitor.net_tx_bps) }}</span>
                </div>
              </div>

              <p class="monitor-ts">
                数据时间：{{ formatCachedAt(overview.server.data.monitor.timestamp) }}
              </p>
            </template>
          </div>
        </section>
      </div>

      <!-- ── 审计日志 ─────────────────────── -->
      <section class="card audit-section">
        <div class="card-header">
          <h3>审计日志</h3>
          <button class="btn btn-sm" :disabled="auditLoading" @click="loadAuditLogs">刷新</button>
        </div>

        <p v-if="auditLoading" class="loading-text">加载中...</p>
        <div v-else-if="auditLogs.length === 0" class="audit-empty">暂无审计记录</div>
        <template v-else>
          <div class="audit-table-wrap">
            <table class="audit-table">
              <thead>
                <tr>
                  <th>事件</th>
                  <th>结果</th>
                  <th>用户</th>
                  <th>IP</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in auditLogs" :key="log.id">
                  <td class="event-cell">
                    <span class="event-name">{{ log.event }}</span>
                    <span v-if="log.reason_code" class="reason-code">{{ log.reason_code }}</span>
                  </td>
                  <td>
                    <span class="badge" :class="resultBadge(log.result)">{{ log.result }}</span>
                  </td>
                  <td class="mono-cell">{{ log.user_id ? log.user_id.slice(0, 8) + '...' : '-' }}</td>
                  <td class="mono-cell">{{ log.client_ip || '-' }}</td>
                  <td class="time-cell">{{ formatAuditTime(log.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="auditTotal > auditPageSize" class="audit-pagination">
            <button
              class="btn btn-sm"
              :disabled="auditPage <= 1"
              @click="onAuditPageChange(auditPage - 1)"
            >
              &larr; 上一页
            </button>
            <span class="page-info">
              第 {{ auditPage }} / {{ Math.ceil(auditTotal / auditPageSize) }} 页（共 {{ auditTotal }} 条）
            </span>
            <button
              class="btn btn-sm"
              :disabled="auditPage >= Math.ceil(auditTotal / auditPageSize)"
              @click="onAuditPageChange(auditPage + 1)"
            >
              下一页 &rarr;
            </button>
          </div>
        </template>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ca-space-5);
}
.page-title { font-size: 18px; font-weight: 600; }
.loading-text { color: var(--ca-text-muted); }
.text-muted { color: var(--ca-text-muted); font-size: 12px; }
.text-danger { color: var(--ca-danger); }
.mono { font-family: monospace; font-size: 13px; }

/* ── Grid layout ─────────────────────── */
.monitor-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ca-space-4);
}
.monitor-card-wide {
  grid-column: span 2;
}

/* ── Card header ─────────────────────── */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ca-space-4);
}
.card-header h3 { font-size: 14px; font-weight: 600; }
.card-actions {
  display: flex;
  align-items: center;
  gap: var(--ca-space-2);
}
.cache-time {
  font-size: 11px;
  color: var(--ca-text-muted);
}
.btn-icon {
  border: none;
  background: none;
  color: var(--ca-text-muted);
  font-size: 16px;
  padding: 2px 6px;
  border-radius: var(--ca-radius);
  line-height: 1;
}
.btn-icon:hover { background: var(--ca-bg); color: var(--ca-primary); }
.btn-icon:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm { padding: 2px 10px; font-size: 12px; }

/* ── Error state ─────────────────────── */
.card-error {
  display: flex;
  flex-direction: column;
  gap: var(--ca-space-3);
  color: var(--ca-danger);
  font-size: 13px;
}

/* ── Billing ─────────────────────── */
.billing-main {
  display: flex;
  align-items: baseline;
  gap: var(--ca-space-2);
  margin-bottom: var(--ca-space-4);
}
.billing-amount { font-size: 28px; font-weight: 700; color: var(--ca-text); }
.billing-currency { font-size: 14px; color: var(--ca-text-muted); }
.billing-details { display: flex; flex-direction: column; gap: var(--ca-space-2); }

/* ── Detail rows ─────────────────────── */
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: var(--ca-space-1) 0;
}
.detail-label { color: var(--ca-text-muted); }
.detail-value { font-weight: 500; }

/* ── OSS ─────────────────────── */
.oss-main {
  display: flex;
  gap: var(--ca-space-6);
  margin-bottom: var(--ca-space-4);
}
.oss-stat-big { display: flex; flex-direction: column; gap: 2px; }
.stat-number { font-size: 20px; font-weight: 600; }
.stat-label { font-size: 12px; color: var(--ca-text-muted); }
.oss-breakdown { display: flex; flex-direction: column; gap: var(--ca-space-1); }

/* ── Server ─────────────────────── */
.server-top {
  display: flex;
  align-items: center;
  gap: var(--ca-space-3);
  margin-bottom: var(--ca-space-4);
}
.server-name { font-weight: 500; }
.server-details { display: flex; flex-direction: column; gap: var(--ca-space-1); }

/* ── Monitor (resource usage) ─────────────────────── */
.monitor-body { display: flex; flex-direction: column; gap: var(--ca-space-4); }
.metric-group { display: flex; flex-direction: column; gap: var(--ca-space-3); }
.metric-row {
  display: flex;
  align-items: center;
  gap: var(--ca-space-3);
}
.metric-label {
  width: 40px;
  font-size: 13px;
  color: var(--ca-text-muted);
  flex-shrink: 0;
}
.metric-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--ca-bg);
  border-radius: 4px;
  overflow: hidden;
}
.metric-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.bar-ok { background: var(--ca-success); }
.bar-warning { background: var(--ca-warning); }
.bar-danger { background: var(--ca-danger); }
.metric-value {
  width: 52px;
  text-align: right;
  font-size: 13px;
  font-weight: 500;
  flex-shrink: 0;
}

.io-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--ca-space-3);
}
.io-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.io-label { font-size: 12px; color: var(--ca-text-muted); }
.io-value { font-size: 14px; font-weight: 500; }

.monitor-ts {
  font-size: 11px;
  color: var(--ca-text-muted);
}
.monitor-unavailable {
  text-align: center;
  padding: var(--ca-space-5);
  color: var(--ca-text-muted);
}
.monitor-unavailable p:first-child { font-weight: 500; color: var(--ca-warning); }
.monitor-hint { font-size: 12px; margin-top: var(--ca-space-2); }

/* ── Audit log ─────────────────────── */
.audit-section { margin-top: var(--ca-space-4); }
.audit-empty {
  text-align: center;
  color: var(--ca-text-muted);
  padding: var(--ca-space-5);
}
.audit-table-wrap { overflow-x: auto; }
.audit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.audit-table th {
  text-align: left;
  padding: var(--ca-space-2) var(--ca-space-3);
  background: var(--ca-bg);
  color: var(--ca-text-muted);
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid var(--ca-border);
}
.audit-table td {
  padding: var(--ca-space-2) var(--ca-space-3);
  border-bottom: 1px solid var(--ca-border);
  vertical-align: middle;
}
.audit-table tr:last-child td { border-bottom: none; }
.event-cell { display: flex; flex-direction: column; gap: 2px; }
.event-name { font-weight: 500; font-size: 13px; }
.reason-code { font-size: 11px; color: var(--ca-text-muted); }
.mono-cell { font-family: monospace; font-size: 12px; color: var(--ca-text-muted); }
.time-cell { font-size: 12px; color: var(--ca-text-muted); white-space: nowrap; }
.audit-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ca-space-3) 0 0;
}
.page-info { font-size: 13px; color: var(--ca-text-muted); }
</style>

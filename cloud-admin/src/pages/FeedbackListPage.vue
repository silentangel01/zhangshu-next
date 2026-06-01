<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DataTable from '@/components/DataTable.vue'
import { listFeedback } from '@/entities/admin-feedback/api'
import type { FeedbackTicket } from '@/entities/admin-feedback/types'
import { useToast } from '@/shared/composables/useToast'

const router = useRouter()
const toast = useToast()
const items = ref<FeedbackTicket[]>([])
const total = ref(0)
const loading = ref(true)
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 20

const columns = [
  { key: 'title', label: '标题' },
  { key: 'category', label: '分类', width: '80px' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'priority', label: '优先级', width: '80px' },
  { key: 'reply_count', label: '回复', width: '60px' },
  { key: 'attachment_count', label: '附件', width: '60px' },
  { key: 'created_at', label: '创建时间', width: '160px' },
]

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const res = await listFeedback({
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '加载反馈列表失败')
    items.value = []
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function openDetail(id: string) {
  router.push(`/feedback/${id}`)
}

function statusBadge(s: string): string {
  const map: Record<string, string> = {
    open: 'badge-info',
    in_progress: 'badge-warning',
    resolved: 'badge-success',
    closed: 'badge-danger',
  }
  return map[s] ?? 'badge-info'
}

function formatDate(d: string): string {
  try {
    return new Date(d).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return d
  }
}
</script>

<template>
  <div>
    <h2 class="page-title">反馈管理 <span class="count">({{ total }})</span></h2>
    <div class="toolbar">
      <input v-model="keyword" class="input search-input" placeholder="搜索标题、邮箱..." @keyup.enter="search" />
      <select v-model="statusFilter" class="input status-select" @change="search">
        <option value="">全部状态</option>
        <option value="open">待处理</option>
        <option value="in_progress">处理中</option>
        <option value="resolved">已解决</option>
        <option value="closed">已关闭</option>
      </select>
    </div>
    <p v-if="loading" class="loading-text">加载中...</p>
    <DataTable
      v-else
      :columns="columns"
      :rows="items as unknown as Record<string, unknown>[]"
      :total="total"
      :page="page"
      :page-size="pageSize"
      @update:page="onPageChange"
    >
      <template #title="{ row }">
        <a href="#" @click.prevent="openDetail((row as unknown as FeedbackTicket).id)">
          {{ (row as unknown as FeedbackTicket).title }}
        </a>
      </template>
      <template #status="{ row }">
        <span class="badge" :class="statusBadge((row as unknown as FeedbackTicket).status)">
          {{ (row as unknown as FeedbackTicket).status }}
        </span>
      </template>
      <template #reply_count="{ row }">
        <span v-if="(row as unknown as FeedbackTicket).reply_count" class="reply-badge">
          {{ (row as unknown as FeedbackTicket).reply_count }}
        </span>
        <span v-else class="text-muted">-</span>
      </template>
      <template #created_at="{ row }">
        {{ formatDate((row as unknown as FeedbackTicket).created_at) }}
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.page-title { font-size: 18px; font-weight: 600; margin-bottom: var(--ca-space-4); }
.count { color: var(--ca-text-muted); font-weight: 400; font-size: 14px; }
.toolbar { display: flex; gap: var(--ca-space-3); margin-bottom: var(--ca-space-4); }
.search-input { max-width: 300px; }
.status-select { max-width: 140px; }
.loading-text { color: var(--ca-text-muted); }
.reply-badge { display: inline-block; padding: 1px 6px; border-radius: 10px; background: var(--ca-info-bg, #eff6ff); color: var(--ca-info, #3b82f6); font-size: 12px; font-weight: 500; }
.text-muted { color: var(--ca-text-muted); }
</style>

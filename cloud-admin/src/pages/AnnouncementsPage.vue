<script setup lang="ts">
import { onMounted, ref } from 'vue'
import DataTable from '@/components/DataTable.vue'
import {
  listAdminAnnouncements,
  createAnnouncement,
  publishAnnouncement,
  archiveAnnouncement,
  deleteAnnouncement,
} from '@/entities/admin-announcement/api'
import type { Announcement } from '@/entities/admin-announcement/types'
import { useToast } from '@/shared/composables/useToast'

const toast = useToast()
const items = ref<Announcement[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const pageSize = 20
const showForm = ref(false)
const newTitle = ref('')
const newBody = ref('')
const newSeverity = ref('info')

const columns = [
  { key: 'title', label: '标题' },
  { key: 'severity', label: '级别', width: '70px' },
  { key: 'status', label: '状态', width: '80px' },
  { key: 'published_at', label: '发布时间', width: '160px' },
  { key: 'actions', label: '操作', width: '200px' },
]

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const res = await listAdminAnnouncements({
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '加载公告列表失败')
    items.value = []
  } finally {
    loading.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}

async function submitNew() {
  try {
    await createAnnouncement({
      title: newTitle.value,
      body: newBody.value,
      severity: newSeverity.value,
    })
    showForm.value = false
    newTitle.value = ''
    newBody.value = ''
    newSeverity.value = 'info'
    await load()
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '创建公告失败')
  }
}

async function publish(id: string) {
  await publishAnnouncement(id)
  await load()
}

async function archive(id: string) {
  await archiveAnnouncement(id)
  await load()
}

async function remove(id: string) {
  if (!confirm('确定删除此公告？')) return
  await deleteAnnouncement(id)
  await load()
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return d
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">公告管理</h2>
      <button class="btn btn-primary" @click="showForm = !showForm">
        {{ showForm ? '取消' : '新建公告' }}
      </button>
    </div>
    <div v-if="showForm" class="card form-card">
      <label class="field">
        <span>标题</span>
        <input v-model="newTitle" class="input" />
      </label>
      <label class="field">
        <span>正文</span>
        <textarea v-model="newBody" class="input body-textarea" rows="4" />
      </label>
      <label class="field inline-field">
        <span>级别</span>
        <select v-model="newSeverity" class="input severity-select">
          <option value="info">通知</option>
          <option value="warning">警告</option>
          <option value="success">好消息</option>
          <option value="critical">紧急</option>
        </select>
      </label>
      <button class="btn btn-primary" :disabled="!newTitle || !newBody" @click="submitNew">创建草稿</button>
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
      <template #status="{ row }">
        <span class="badge" :class="(row as unknown as Announcement).status === 'published' ? 'badge-success' : 'badge-info'">
          {{ (row as unknown as Announcement).status }}
        </span>
      </template>
      <template #published_at="{ row }">
        {{ formatDate((row as unknown as Announcement).published_at) }}
      </template>
      <template #actions="{ row }">
        <button v-if="(row as unknown as Announcement).status === 'draft'" class="btn-sm" @click="publish((row as unknown as Announcement).id)">发布</button>
        <button v-if="(row as unknown as Announcement).status === 'published'" class="btn-sm" @click="archive((row as unknown as Announcement).id)">归档</button>
        <button class="btn-sm btn-sm-danger" @click="remove((row as unknown as Announcement).id)">删除</button>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--ca-space-4); }
.page-title { font-size: 18px; font-weight: 600; }
.form-card { margin-bottom: var(--ca-space-4); display: flex; flex-direction: column; gap: var(--ca-space-3); }
.field { display: flex; flex-direction: column; gap: var(--ca-space-1); font-size: 13px; color: var(--ca-text-muted); }
.inline-field { flex-direction: row; align-items: center; gap: var(--ca-space-3); }
.body-textarea { resize: vertical; }
.severity-select { max-width: 120px; }
.loading-text { color: var(--ca-text-muted); }
.btn-sm { padding: 2px 8px; border: 1px solid var(--ca-border); border-radius: 4px; background: var(--ca-surface); font-size: 12px; cursor: pointer; margin-right: 4px; }
.btn-sm:hover { border-color: var(--ca-primary); color: var(--ca-primary); }
.btn-sm-danger:hover { border-color: var(--ca-danger); color: var(--ca-danger); }
</style>

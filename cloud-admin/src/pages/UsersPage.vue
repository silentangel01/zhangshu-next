<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DataTable from '@/components/DataTable.vue'
import { listUsers } from '@/entities/admin-user/api'
import type { AdminUserListItem } from '@/entities/admin-user/types'
import { useToast } from '@/shared/composables/useToast'

const router = useRouter()
const toast = useToast()
const items = ref<AdminUserListItem[]>([])
const total = ref(0)
const loading = ref(true)
const keyword = ref('')
const page = ref(1)
const pageSize = 20

const columns = [
  { key: 'email', label: '邮箱' },
  { key: 'display_name', label: '显示名', width: '120px' },
  { key: 'login_count', label: '登录次数', width: '80px' },
  { key: 'cloud_project_count', label: '项目', width: '60px' },
  { key: 'cloud_backup_count', label: '备份', width: '60px' },
  { key: 'feedback_count', label: '反馈', width: '60px' },
  { key: 'created_at', label: '注册时间', width: '160px' },
]

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const res = await listUsers({
      keyword: keyword.value || undefined,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '加载用户列表失败')
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
  router.push(`/users/${id}`)
}

function formatDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString('zh-CN')
  } catch {
    return d
  }
}
</script>

<template>
  <div>
    <h2 class="page-title">用户列表 <span class="count">({{ total }})</span></h2>
    <div class="toolbar">
      <input v-model="keyword" class="input search-input" placeholder="搜索邮箱、显示名..." @keyup.enter="search" />
      <button class="btn" @click="search">搜索</button>
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
      <template #email="{ row }">
        <a href="#" @click.prevent="openDetail((row as unknown as AdminUserListItem).id)">
          {{ (row as unknown as AdminUserListItem).email }}
        </a>
      </template>
      <template #created_at="{ row }">
        {{ formatDate((row as unknown as AdminUserListItem).created_at) }}
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.page-title { font-size: 18px; font-weight: 600; margin-bottom: var(--ca-space-4); }
.count { color: var(--ca-text-muted); font-weight: 400; font-size: 14px; }
.toolbar { display: flex; gap: var(--ca-space-3); margin-bottom: var(--ca-space-4); }
.search-input { max-width: 300px; }
.loading-text { color: var(--ca-text-muted); }
</style>

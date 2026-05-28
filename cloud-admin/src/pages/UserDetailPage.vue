<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserDetail, toggleUserActive, forceLogoutUser } from '@/entities/admin-user/api'
import type { AdminUserDetail } from '@/entities/admin-user/types'
import { useToast } from '@/shared/composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const user = ref<AdminUserDetail | null>(null)
const loading = ref(true)
const actionLoading = ref(false)

onMounted(async () => {
  try {
    user.value = await getUserDetail(route.params.id as string)
  } catch {
    router.push('/users')
  } finally {
    loading.value = false
  }
})

async function handleToggleActive() {
  if (!user.value) return
  const action = user.value.is_active ? '禁用' : '启用'
  if (!confirm(`确定${action}此用户？`)) return
  actionLoading.value = true
  try {
    const res = await toggleUserActive(user.value.id)
    user.value.is_active = res.is_active
    toast.success(`已${action}用户`)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : `${action}失败`)
  } finally {
    actionLoading.value = false
  }
}

async function handleForceLogout() {
  if (!user.value) return
  if (!confirm('确定强制下线此用户？该操作将撤销其所有活跃会话。')) return
  actionLoading.value = true
  try {
    const res = await forceLogoutUser(user.value.id)
    toast.success(`已强制下线，撤销 ${res.tokens_revoked} 个会话`)
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '强制下线失败')
  } finally {
    actionLoading.value = false
  }
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return d
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
</script>

<template>
  <div>
    <button class="btn back-btn" @click="router.push('/users')">&larr; 返回列表</button>
    <p v-if="loading" class="loading-text">加载中...</p>
    <template v-else-if="user">
      <div class="card profile-card">
        <h2>{{ user.display_name }}</h2>
        <p class="email">{{ user.email }}</p>
        <p v-if="user.signature" class="signature">{{ user.signature }}</p>
        <div class="info-grid">
          <div><strong>注册时间</strong><span>{{ formatDate(user.created_at) }}</span></div>
          <div><strong>最后登录</strong><span>{{ formatDate(user.last_login_at) }}</span></div>
          <div><strong>登录次数</strong><span>{{ user.login_count }}</span></div>
          <div><strong>密码修改</strong><span>{{ formatDate(user.password_changed_at) }}</span></div>
          <div><strong>云项目</strong><span>{{ user.cloud_project_count }}</span></div>
          <div><strong>云备份</strong><span>{{ user.cloud_backup_count }}</span></div>
          <div><strong>存储用量</strong><span>{{ formatBytes(user.total_storage_bytes) }}</span></div>
          <div><strong>反馈数</strong><span>{{ user.feedback_count }}</span></div>
        </div>
      </div>
      <div class="card section-card">
        <h3>管理操作</h3>
        <div class="admin-actions">
          <button
            class="btn"
            :class="user.is_active ? 'btn-warning' : 'btn-success'"
            :disabled="actionLoading"
            @click="handleToggleActive"
          >
            {{ user.is_active ? '禁用用户' : '启用用户' }}
          </button>
          <button
            class="btn btn-danger"
            :disabled="actionLoading"
            @click="handleForceLogout"
          >
            强制下线
          </button>
        </div>
      </div>
      <div v-if="user.recent_activity.length" class="card section-card">
        <h3>最近活动</h3>
        <ul class="activity-list">
          <li v-for="(a, i) in user.recent_activity" :key="i">
            <span class="event-type">{{ a.event_type }}</span>
            <span class="event-time">{{ formatDate(a.created_at) }}</span>
          </li>
        </ul>
      </div>
      <div v-if="user.recent_feedback.length" class="card section-card">
        <h3>最近反馈</h3>
        <ul class="feedback-list">
          <li v-for="f in user.recent_feedback" :key="f.id">
            <RouterLink :to="`/feedback/${f.id}`">{{ f.title }}</RouterLink>
            <span class="badge badge-info">{{ f.status }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back-btn { margin-bottom: var(--ca-space-4); }
.loading-text { color: var(--ca-text-muted); }
.profile-card { margin-bottom: var(--ca-space-4); }
.profile-card h2 { font-size: 18px; margin-bottom: var(--ca-space-1); }
.email { color: var(--ca-text-muted); margin-bottom: var(--ca-space-3); }
.signature { font-style: italic; color: var(--ca-text-muted); margin-bottom: var(--ca-space-4); }
.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--ca-space-3); }
.info-grid div { display: flex; justify-content: space-between; padding: var(--ca-space-2) 0; border-bottom: 1px solid var(--ca-border); }
.info-grid strong { color: var(--ca-text-muted); font-weight: 500; }
.section-card { margin-bottom: var(--ca-space-4); }
.section-card h3 { font-size: 15px; margin-bottom: var(--ca-space-3); }
.activity-list, .feedback-list { list-style: none; }
.activity-list li, .feedback-list li { display: flex; justify-content: space-between; padding: var(--ca-space-2) 0; border-bottom: 1px solid var(--ca-border); font-size: 13px; }
.event-type { font-weight: 500; }
.event-time { color: var(--ca-text-muted); }
.admin-actions { display: flex; gap: var(--ca-space-3); }
.btn-warning { background: var(--ca-warning, #f59e0b); color: #fff; border-color: var(--ca-warning, #f59e0b); }
.btn-warning:hover { opacity: 0.9; }
.btn-success { background: var(--ca-success, #22c55e); color: #fff; border-color: var(--ca-success, #22c55e); }
.btn-success:hover { opacity: 0.9; }
.btn-danger { background: var(--ca-danger, #ef4444); color: #fff; border-color: var(--ca-danger, #ef4444); }
.btn-danger:hover { opacity: 0.9; }
</style>

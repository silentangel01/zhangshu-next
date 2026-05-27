<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserDetail } from '@/entities/admin-user/api'
import type { AdminUserDetail } from '@/entities/admin-user/types'

const route = useRoute()
const router = useRouter()
const user = ref<AdminUserDetail | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    user.value = await getUserDetail(route.params.id as string)
  } catch {
    router.push('/users')
  } finally {
    loading.value = false
  }
})

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
</style>

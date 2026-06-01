<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { listFeedbackHistory, listFeedbackReplies } from '@/entities/feedback/api'
import type { FeedbackHistoryItem, FeedbackReply } from '@/entities/feedback/types'
import { getCloudAccountStatus } from '@/entities/cloud/api'

const router = useRouter()

const loading = ref(true)
const isLoggedIn = ref(false)
const cloudAvailable = ref(false)
const items = ref<FeedbackHistoryItem[]>([])
const total = ref(0)
const expandedId = ref<string | null>(null)
const expandedReplies = ref<Record<string, FeedbackReply[]>>({})
const repliesLoading = ref<Record<string, boolean>>({})
const errorMessage = ref('')

const CATEGORY_LABELS: Record<string, string> = {
  bug: '问题反馈',
  suggestion: '功能建议',
  data_loss: '数据风险',
  cloud: '云服务问题',
  ui: '界面体验',
  other: '其他',
}

const STATUS_LABELS: Record<string, string> = {
  open: '待处理',
  triaged: '已分类',
  in_progress: '处理中',
  closed: '已关闭',
  spam: '垃圾',
}

onMounted(async () => {
  try {
    const status = await getCloudAccountStatus()
    cloudAvailable.value = status.cloud_available
    isLoggedIn.value = status.logged_in

    if (status.logged_in) {
      await loadHistory()
    }
  } catch {
    errorMessage.value = '无法加载反馈历史。'
  } finally {
    loading.value = false
  }
})

async function loadHistory() {
  loading.value = true
  try {
    const res = await listFeedbackHistory()
    items.value = res.items
    total.value = res.total
  } catch (err: unknown) {
    const msg = (err as { message?: string })?.message
    errorMessage.value = msg || '无法加载反馈历史。'
  } finally {
    loading.value = false
  }
}

async function toggleExpand(item: FeedbackHistoryItem) {
  if (expandedId.value === item.id) {
    expandedId.value = null
    return
  }
  expandedId.value = item.id
  if (!expandedReplies.value[item.id]) {
    repliesLoading.value[item.id] = true
    try {
      const res = await listFeedbackReplies(item.id)
      expandedReplies.value[item.id] = res.items
    } catch {
      expandedReplies.value[item.id] = []
    } finally {
      repliesLoading.value[item.id] = false
    }
  }
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
  <div class="history-page">
    <header class="page-header">
      <button class="btn-back" @click="router.push('/account')">&larr; 返回账户</button>
      <h1 class="page-title">我的反馈</h1>
    </header>

    <p v-if="loading" class="loading-text">加载中...</p>

    <template v-else>
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>

      <div v-if="!isLoggedIn" class="not-logged-in">
        <p class="info-text">
          {{ cloudAvailable ? '登录后才能查看反馈历史。' : '云服务暂未配置。' }}
        </p>
        <button v-if="cloudAvailable" class="btn-primary" @click="router.push('/projects')">
          去登录
        </button>
      </div>

      <template v-else>
        <p v-if="!items.length" class="empty-text">暂无反馈记录。</p>
        <div v-else class="feedback-list">
          <div
            v-for="item in items"
            :key="item.id"
            class="card feedback-card"
            :class="{ expanded: expandedId === item.id }"
          >
            <div class="feedback-header" @click="toggleExpand(item)">
              <div class="feedback-title-row">
                <span class="category-badge">{{ CATEGORY_LABELS[item.category] ?? item.category }}</span>
                <h3 class="feedback-title">{{ item.title }}</h3>
              </div>
              <div class="feedback-meta">
                <span class="status-badge" :class="`status-${item.status}`">
                  {{ STATUS_LABELS[item.status] ?? item.status }}
                </span>
                <span v-if="item.reply_count > 0" class="reply-count-badge">
                  {{ item.reply_count }} 条回复
                </span>
                <span class="feedback-date">{{ formatDate(item.created_at) }}</span>
              </div>
            </div>
            <div v-if="expandedId === item.id" class="feedback-body">
              <div class="description-block">
                <h4>详细描述</h4>
                <p class="description-text">{{ item.description }}</p>
              </div>
              <div class="replies-block">
                <h4>管理员回复</h4>
                <p v-if="repliesLoading[item.id]" class="loading-text">加载中...</p>
                <p
                  v-else-if="!expandedReplies[item.id]?.length"
                  class="no-replies"
                >
                  暂无回复
                </p>
                <div v-else class="reply-list">
                  <div v-for="reply in expandedReplies[item.id]" :key="reply.id" class="reply-item">
                    <div class="reply-header">
                      <span class="reply-author-badge">
                        {{ reply.author_type === 'admin' ? '管理员' : '系统' }}
                      </span>
                      <span v-if="reply.author_display_name" class="reply-author">
                        {{ reply.author_display_name }}
                      </span>
                      <span class="reply-date">{{ formatDate(reply.created_at) }}</span>
                    </div>
                    <p class="reply-content">{{ reply.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 700px;
  margin: 0 auto;
  padding: var(--zs-space-5);
}

.page-header {
  margin-bottom: var(--zs-space-5);
}

.btn-back {
  padding: var(--zs-space-2) 0;
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  margin-bottom: var(--zs-space-2);
}

.btn-back:hover {
  color: var(--zs-color-primary);
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.loading-text {
  color: var(--zs-color-text-muted);
  text-align: center;
  padding: var(--zs-space-6);
}

.message {
  padding: var(--zs-space-3) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  margin-bottom: var(--zs-space-4);
  font-size: 0.9rem;
}

.message-error {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
}

.not-logged-in {
  text-align: center;
  padding: var(--zs-space-6);
}

.info-text {
  color: var(--zs-color-text-muted);
  margin-bottom: var(--zs-space-4);
}

.btn-primary {
  padding: var(--zs-space-2) var(--zs-space-4);
  border: none;
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

.empty-text {
  color: var(--zs-color-text-muted);
  text-align: center;
  padding: var(--zs-space-6);
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.feedback-card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  overflow: hidden;
}

.feedback-card.expanded {
  border-color: var(--zs-color-primary);
}

.feedback-header {
  padding: var(--zs-space-3) var(--zs-space-4);
  cursor: pointer;
}

.feedback-header:hover {
  background: var(--zs-color-surface-soft);
}

.feedback-title-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  margin-bottom: var(--zs-space-2);
}

.category-badge {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--zs-color-surface-soft, #f5f5f5);
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 500;
}

.feedback-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feedback-meta {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  flex-wrap: wrap;
  font-size: 0.8rem;
}

.status-badge {
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-open {
  background: #eff6ff;
  color: #3b82f6;
}

.status-triaged,
.status-in_progress {
  background: #fffbeb;
  color: #f59e0b;
}

.status-closed {
  background: #f0fdf4;
  color: #22c55e;
}

.status-spam {
  background: #fef2f2;
  color: #ef4444;
}

.reply-count-badge {
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--zs-color-primary, #3b82f6);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 500;
}

.feedback-date {
  color: var(--zs-color-text-muted);
  margin-left: auto;
}

.feedback-body {
  padding: 0 var(--zs-space-4) var(--zs-space-4);
  border-top: 1px solid var(--zs-color-border-soft);
}

.description-block {
  margin-top: var(--zs-space-3);
  margin-bottom: var(--zs-space-4);
}

.description-block h4,
.replies-block h4 {
  margin: 0 0 var(--zs-space-2);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--zs-color-text-muted);
}

.description-text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 0.9rem;
}

.no-replies {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  margin: 0;
}

.reply-list {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-2);
}

.reply-item {
  padding: var(--zs-space-3);
  background: var(--zs-color-surface-soft, #f9fafb);
  border-radius: var(--zs-radius-sm);
}

.reply-header {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  margin-bottom: var(--zs-space-2);
  font-size: 0.8rem;
}

.reply-author-badge {
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--zs-color-primary, #3b82f6);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 500;
}

.reply-author {
  font-weight: 500;
}

.reply-date {
  color: var(--zs-color-text-muted);
  margin-left: auto;
}

.reply-content {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.5;
  font-size: 0.85rem;
}
</style>

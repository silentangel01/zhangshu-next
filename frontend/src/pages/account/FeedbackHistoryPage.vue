<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

const activeCount = computed(
  () =>
    items.value.filter((item) => ['open', 'triaged', 'in_progress'].includes(item.status)).length,
)
const repliedCount = computed(() => items.value.filter((item) => item.reply_count > 0).length)

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
      <div class="page-heading">
        <p class="page-kicker">章枢 · 账户档案</p>
        <h1 class="page-title">我的反馈</h1>
        <p class="page-subtitle">查看问题处理进度、补充说明与管理员回复。</p>
      </div>
    </header>

    <div class="history-layout">
      <aside class="history-summary">
        <div class="summary-header">
          <span class="summary-index">反馈档案 · 02</span>
          <span class="summary-state">
            {{ loading ? '正在同步' : isLoggedIn ? '记录已载入' : '等待登录' }}
          </span>
        </div>

        <div class="summary-copy">
          <p class="summary-label">反馈往来</p>
          <h2>处理记录概览</h2>
          <p>反馈会按提交时间归档；展开记录即可查看完整描述和处理回复。</p>
        </div>

        <dl class="summary-metrics">
          <div>
            <dt>全部记录</dt>
            <dd>{{ loading || !isLoggedIn ? '—' : total }}</dd>
          </div>
          <div>
            <dt>处理中</dt>
            <dd>{{ loading || !isLoggedIn ? '—' : activeCount }}</dd>
          </div>
          <div>
            <dt>已有回复</dt>
            <dd>{{ loading || !isLoggedIn ? '—' : repliedCount }}</dd>
          </div>
        </dl>

        <p class="summary-note">需要提交新问题时，可使用窗口右下角的“意见反馈”。</p>
      </aside>

      <section class="history-content">
        <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>

        <div v-if="loading" class="state-card" aria-live="polite">
          <span class="loading-dot" aria-hidden="true" />
          <div>
            <h2>正在读取反馈记录</h2>
            <p>正在连接云端并整理历史反馈…</p>
          </div>
        </div>

        <template v-else>
          <div v-if="!isLoggedIn" class="state-card not-logged-in">
            <div>
              <h2>{{ cloudAvailable ? '登录后查看反馈档案' : '云服务暂未配置' }}</h2>
              <p class="info-text">
                {{
                  cloudAvailable
                    ? '登录后才能查看反馈历史和管理员回复。'
                    : '请配置云服务后再使用反馈记录。'
                }}
              </p>
            </div>
            <button v-if="cloudAvailable" class="btn-primary" @click="router.push('/projects')">
              去登录
            </button>
          </div>

          <template v-else>
            <div v-if="!items.length" class="state-card empty-state">
              <div>
                <h2>还没有反馈记录</h2>
                <p>提交后的问题、建议和处理回复会统一归档在这里。</p>
              </div>
            </div>

            <div v-else class="feedback-list">
              <article
                v-for="item in items"
                :key="item.id"
                class="feedback-card"
                :class="{ expanded: expandedId === item.id }"
              >
                <button
                  type="button"
                  class="feedback-header"
                  :aria-expanded="expandedId === item.id"
                  @click="toggleExpand(item)"
                >
                  <span class="feedback-heading">
                    <span class="feedback-title-row">
                      <span class="category-badge">{{
                        CATEGORY_LABELS[item.category] ?? item.category
                      }}</span>
                      <span class="feedback-title">{{ item.title }}</span>
                    </span>
                    <span class="feedback-preview">{{ item.description }}</span>
                  </span>

                  <span class="feedback-meta">
                    <span class="status-badge" :class="`status-${item.status}`">
                      {{ STATUS_LABELS[item.status] ?? item.status }}
                    </span>
                    <span v-if="item.reply_count > 0" class="reply-count-badge">
                      {{ item.reply_count }} 条回复
                    </span>
                    <span class="feedback-date">{{ formatDate(item.created_at) }}</span>
                  </span>

                  <span
                    class="feedback-toggle"
                    :class="{ open: expandedId === item.id }"
                    aria-hidden="true"
                    >›</span
                  >
                </button>

                <div v-if="expandedId === item.id" class="feedback-body">
                  <div class="description-block">
                    <h4>详细描述</h4>
                    <p class="description-text">{{ item.description }}</p>
                  </div>
                  <div class="replies-block">
                    <h4>管理员回复</h4>
                    <p v-if="repliesLoading[item.id]" class="reply-loading">加载中...</p>
                    <p v-else-if="!expandedReplies[item.id]?.length" class="no-replies">暂无回复</p>
                    <div v-else class="reply-list">
                      <div
                        v-for="reply in expandedReplies[item.id]"
                        :key="reply.id"
                        class="reply-item"
                      >
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
              </article>
            </div>
          </template>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  width: 100%;
  max-width: 1180px;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 36px 40px 64px;
}

.page-header {
  display: grid;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-6);
  padding-bottom: var(--zs-space-5);
  border-bottom: 1px solid var(--zs-color-border);
}

.btn-back {
  justify-self: start;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-back:hover {
  color: var(--zs-color-primary);
}

.page-heading {
  display: grid;
  gap: var(--zs-space-1);
}

.page-kicker,
.page-subtitle {
  margin: 0;
}

.page-kicker,
.summary-index {
  color: var(--zs-color-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.page-title {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.page-subtitle {
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
}

.history-layout {
  display: grid;
  grid-template-columns: minmax(270px, 0.72fr) minmax(0, 1.78fr);
  gap: var(--zs-space-6);
  align-items: start;
}

.history-summary {
  position: sticky;
  top: var(--zs-space-6);
  display: flex;
  flex-direction: column;
  min-height: 500px;
  box-sizing: border-box;
  padding: var(--zs-space-5);
  border: 1px solid var(--zs-color-border);
  border-top: 3px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-md);
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--zs-color-primary) 8%, transparent),
      transparent 48%
    ),
    var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
}

.summary-state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-success);
  font-size: 0.72rem;
  font-weight: 700;
}

.summary-state::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  content: '';
}

.summary-copy {
  margin: var(--zs-space-7) 0 var(--zs-space-5);
}

.summary-label {
  margin: 0 0 var(--zs-space-2);
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.summary-copy h2 {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.35rem;
}

.summary-copy > p:last-child {
  margin: var(--zs-space-3) 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.7;
}

.summary-metrics {
  margin: 0;
  border-top: 1px solid var(--zs-color-border-soft);
}

.summary-metrics > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  padding: var(--zs-space-3) 0;
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.summary-metrics dt {
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
}

.summary-metrics dd {
  margin: 0;
  font-family: Georgia, serif;
  font-size: 1.05rem;
  font-weight: 700;
}

.summary-note {
  margin: auto 0 0;
  padding-top: var(--zs-space-5);
  color: var(--zs-color-text-faint);
  font-size: 0.76rem;
  line-height: 1.65;
}

.history-content {
  min-width: 0;
}

.message {
  width: 100%;
  box-sizing: border-box;
  padding: var(--zs-space-3) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  margin-bottom: var(--zs-space-4);
  font-size: 0.9rem;
}

.message-error {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
}

.state-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-5);
  min-height: 230px;
  box-sizing: border-box;
  padding: 36px 40px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.state-card h2 {
  margin: 0;
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1.2rem;
}

.state-card p {
  margin: var(--zs-space-2) 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  line-height: 1.65;
}

.loading-dot {
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--zs-color-primary);
  box-shadow: 0 0 0 7px color-mix(in srgb, var(--zs-color-primary) 12%, transparent);
  animation: feedback-pulse 1.4s ease-in-out infinite;
}

.info-text {
  margin-bottom: 0;
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

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.feedback-card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  overflow: hidden;
  box-shadow: var(--zs-shadow-sm);
  transition:
    border-color var(--zs-duration-fast) ease,
    transform var(--zs-duration-fast) ease,
    box-shadow var(--zs-duration-fast) ease;
}

.feedback-card.expanded {
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-md);
}

.feedback-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--zs-space-5);
  width: 100%;
  box-sizing: border-box;
  padding: var(--zs-space-4) var(--zs-space-5);
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background var(--zs-duration-fast) ease;
}

.feedback-header:hover {
  background: var(--zs-color-surface-soft);
}

.feedback-heading {
  display: block;
  min-width: 0;
}

.feedback-title-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
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
  font-family: 'Songti SC', 'STSong', var(--zs-font-ui);
  font-size: 1rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feedback-preview {
  display: block;
  margin: var(--zs-space-2) 0 0;
  overflow: hidden;
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feedback-meta {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: var(--zs-space-2);
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
  white-space: nowrap;
}

.feedback-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 50%;
  color: var(--zs-color-text-muted);
  font-size: 1.35rem;
  line-height: 1;
  transform: rotate(0deg);
  transition:
    color var(--zs-duration-fast) ease,
    border-color var(--zs-duration-fast) ease,
    transform var(--zs-duration-normal) var(--zs-ease-emphasized);
}

.feedback-toggle.open {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
  transform: rotate(90deg);
}

.feedback-body {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: var(--zs-space-6);
  padding: var(--zs-space-5);
  border-top: 1px solid var(--zs-color-border-soft);
  background: color-mix(in srgb, var(--zs-color-surface-soft) 45%, transparent);
}

.description-block {
  margin: 0;
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

.reply-loading {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
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

@keyframes feedback-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-dot {
    animation: none;
  }

  .feedback-card,
  .feedback-header,
  .feedback-toggle {
    transition: none;
  }
}

@media (max-width: 900px) {
  .history-page {
    padding-right: var(--zs-space-6);
    padding-left: var(--zs-space-6);
  }

  .history-layout {
    grid-template-columns: 1fr;
  }

  .history-summary {
    position: relative;
    top: auto;
    min-height: 0;
  }

  .summary-note {
    margin-top: var(--zs-space-5);
  }
}

@media (max-width: 640px) {
  .history-page {
    padding: var(--zs-space-5) var(--zs-space-3) var(--zs-space-8);
  }

  .page-title {
    font-size: 1.65rem;
  }

  .state-card {
    align-items: flex-start;
    flex-direction: column;
    min-height: 0;
    padding: var(--zs-space-5);
  }

  .feedback-header {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--zs-space-3);
    padding: var(--zs-space-4);
  }

  .feedback-meta {
    grid-column: 1 / -1;
    align-items: center;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .feedback-toggle {
    grid-column: 2;
    grid-row: 1;
  }

  .feedback-body {
    grid-template-columns: 1fr;
    gap: var(--zs-space-5);
    padding: var(--zs-space-4);
  }

  .feedback-date {
    margin-left: auto;
  }
}
</style>

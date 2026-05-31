<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getFeedback,
  updateFeedback,
  listAttachments,
  getAttachmentDownloadUrl,
  listReplies,
  createReply,
} from '@/entities/admin-feedback/api'
import type {
  FeedbackTicket,
  FeedbackAttachment,
  FeedbackReply,
} from '@/entities/admin-feedback/types'
import { useToast } from '@/shared/composables/useToast'
import { useAdminSession } from '@/shared/composables/useAdminSession'
import RiskActionDialog from '@/components/RiskActionDialog.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { hasPermission } = useAdminSession()
const feedback = ref<FeedbackTicket | null>(null)
const attachments = ref<FeedbackAttachment[]>([])
const replies = ref<FeedbackReply[]>([])
const loading = ref(true)
const saving = ref(false)
const newStatus = ref('')
const newPriority = ref('')
const newNote = ref('')
const replyContent = ref('')
const replySubmitting = ref(false)

// Download confirmation dialog
const showDownloadDialog = ref(false)
const pendingAttachment = ref<FeedbackAttachment | null>(null)
const dialogRef = ref<InstanceType<typeof RiskActionDialog> | null>(null)

onMounted(async () => {
  try {
    const id = route.params.id as string
    feedback.value = await getFeedback(id)
    newStatus.value = feedback.value.status
    newPriority.value = feedback.value.priority ?? ''
    newNote.value = feedback.value.admin_note ?? ''
    if (feedback.value.attachment_count > 0) {
      attachments.value = await listAttachments(id)
    }
    const repliesRes = await listReplies(id)
    replies.value = repliesRes.items
  } catch {
    router.push('/feedback')
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!feedback.value) return
  saving.value = true
  try {
    feedback.value = await updateFeedback(feedback.value.id, {
      status: newStatus.value,
      priority: newPriority.value || undefined,
      admin_note: newNote.value || undefined,
    })
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitReply() {
  if (!feedback.value || !replyContent.value.trim()) return
  replySubmitting.value = true
  try {
    const reply = await createReply(feedback.value.id, {
      content: replyContent.value.trim(),
    })
    replies.value.push(reply)
    replyContent.value = ''
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '发送回复失败')
  } finally {
    replySubmitting.value = false
  }
}

function requestDownload(att: FeedbackAttachment) {
  pendingAttachment.value = att
  showDownloadDialog.value = true
}

async function handleDownloadConfirm(payload: { reason: string }) {
  if (!feedback.value || !pendingAttachment.value) return
  dialogRef.value?.setLoading(true)
  try {
    const { download_url } = await getAttachmentDownloadUrl(
      feedback.value.id,
      pendingAttachment.value.id,
      payload.reason,
    )
    window.open(download_url, '_blank')
    showDownloadDialog.value = false
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '下载失败')
  } finally {
    dialogRef.value?.setLoading(false)
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
    <button class="btn back-btn" @click="router.push('/feedback')">&larr; 返回列表</button>
    <p v-if="loading" class="loading-text">加载中...</p>
    <template v-else-if="feedback">
      <div class="card detail-card">
        <h2>{{ feedback.title }}</h2>
        <div class="meta-row">
          <span class="badge badge-info">{{ feedback.category }}</span>
          <span class="badge" :class="feedback.status === 'open' ? 'badge-warning' : 'badge-success'">
            {{ feedback.status }}
          </span>
          <span class="meta-text">附件: {{ feedback.attachment_count }}</span>
          <span class="meta-text">{{ feedback.platform ?? '' }} {{ feedback.app_version ?? '' }}</span>
        </div>
        <div class="description">{{ feedback.description }}</div>
        <div v-if="feedback.client_diagnostics_json" class="diagnostics">
          <strong>诊断信息:</strong>
          <pre>{{ feedback.client_diagnostics_json }}</pre>
        </div>
      </div>
      <div v-if="attachments.length" class="card attachments-card">
        <h3>附件 ({{ attachments.length }})</h3>
        <p class="attachment-warning">附件可能包含用户作品或隐私内容，下载操作将被审计记录。</p>
        <ul class="attachment-list">
          <li v-for="att in attachments" :key="att.id">
            <span class="att-name">{{ att.filename }}</span>
            <span class="att-size">{{ formatBytes(att.size_bytes) }}</span>
            <button v-if="hasPermission('feedback:attachment_download')" class="btn-sm" @click="requestDownload(att)">下载</button>
          </li>
        </ul>
      </div>
      <div class="card replies-card">
        <h3>回复记录</h3>
        <div v-if="replies.length" class="reply-list">
          <div v-for="reply in replies" :key="reply.id" class="reply-item">
            <div class="reply-header">
              <span class="badge badge-info">{{ reply.author_type === 'admin' ? '管理员' : '系统' }}</span>
              <span v-if="reply.author_display_name" class="reply-author">{{ reply.author_display_name }}</span>
              <span class="reply-time">{{ formatDate(reply.created_at) }}</span>
            </div>
            <div class="reply-content">{{ reply.content }}</div>
          </div>
        </div>
        <p v-else class="empty-text">暂无回复</p>
        <div v-if="hasPermission('feedback:reply')" class="reply-form">
          <textarea
            v-model="replyContent"
            class="input reply-input"
            rows="3"
            placeholder="输入回复内容（用户可在客户端看到）..."
          />
          <button
            class="btn btn-primary"
            :disabled="replySubmitting || !replyContent.trim()"
            @click="submitReply"
          >
            {{ replySubmitting ? '发送中...' : '发送回复' }}
          </button>
        </div>
      </div>
      <div v-if="hasPermission('feedback:manage')" class="card update-card">
        <h3>更新状态</h3>
        <div class="form-row">
          <select v-model="newStatus" class="input">
            <option value="open">待处理</option>
            <option value="in_progress">处理中</option>
            <option value="resolved">已解决</option>
            <option value="closed">已关闭</option>
          </select>
          <select v-model="newPriority" class="input">
            <option value="">无优先级</option>
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="urgent">紧急</option>
          </select>
        </div>
        <textarea v-model="newNote" class="input note-input" rows="3" placeholder="管理员备注..." />
        <button class="btn btn-primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </template>

    <RiskActionDialog
      v-if="showDownloadDialog"
      ref="dialogRef"
      title="下载反馈附件"
      message="附件可能包含用户作品或隐私内容。下载操作将被记录到审计日志。"
      variant="warning"
      confirm-label="下载"
      :require-reason="true"
      @confirm="handleDownloadConfirm"
      @cancel="showDownloadDialog = false"
    />
  </div>
</template>

<style scoped>
.back-btn { margin-bottom: var(--ca-space-4); }
.loading-text { color: var(--ca-text-muted); }
.detail-card { margin-bottom: var(--ca-space-4); }
.detail-card h2 { font-size: 18px; margin-bottom: var(--ca-space-3); }
.meta-row { display: flex; gap: var(--ca-space-2); align-items: center; flex-wrap: wrap; margin-bottom: var(--ca-space-4); }
.meta-text { font-size: 12px; color: var(--ca-text-muted); }
.description { white-space: pre-wrap; line-height: 1.6; margin-bottom: var(--ca-space-4); }
.diagnostics { font-size: 12px; color: var(--ca-text-muted); }
.diagnostics pre { margin-top: var(--ca-space-2); white-space: pre-wrap; word-break: break-all; }
.update-card h3 { font-size: 15px; margin-bottom: var(--ca-space-3); }
.form-row { display: flex; gap: var(--ca-space-3); margin-bottom: var(--ca-space-3); }
.note-input { margin-bottom: var(--ca-space-3); resize: vertical; }
.attachments-card { margin-bottom: var(--ca-space-4); }
.attachments-card h3 { font-size: 15px; margin-bottom: var(--ca-space-3); }
.attachment-list { list-style: none; }
.attachment-warning { font-size: 12px; color: var(--ca-warning, #f59e0b); margin-bottom: var(--ca-space-2); }
.attachment-list li { display: flex; align-items: center; gap: var(--ca-space-3); padding: var(--ca-space-2) 0; border-bottom: 1px solid var(--ca-border); font-size: 13px; }
.att-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.att-size { color: var(--ca-text-muted); min-width: 60px; text-align: right; }
.replies-card { margin-bottom: var(--ca-space-4); }
.replies-card h3 { font-size: 15px; margin-bottom: var(--ca-space-3); }
.reply-list { margin-bottom: var(--ca-space-3); }
.reply-item { padding: var(--ca-space-3); border: 1px solid var(--ca-border); border-radius: 6px; margin-bottom: var(--ca-space-2); }
.reply-header { display: flex; align-items: center; gap: var(--ca-space-2); margin-bottom: var(--ca-space-2); font-size: 12px; }
.reply-author { font-weight: 500; }
.reply-time { color: var(--ca-text-muted); margin-left: auto; }
.reply-content { white-space: pre-wrap; line-height: 1.5; font-size: 13px; }
.empty-text { color: var(--ca-text-muted); font-size: 13px; margin-bottom: var(--ca-space-3); }
.reply-form { display: flex; flex-direction: column; gap: var(--ca-space-2); }
.reply-input { resize: vertical; }
</style>

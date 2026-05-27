<script setup lang="ts">
import { ref } from 'vue'

import { submitFeedback, listFeedbackReplies } from '@/entities/feedback/api'
import type {
  FeedbackCategory,
  FeedbackReply,
  FeedbackSubmitResponse,
} from '@/entities/feedback/types'

const emit = defineEmits<{
  close: []
}>()

const CATEGORIES: { value: FeedbackCategory; label: string }[] = [
  { value: 'bug', label: '问题反馈' },
  { value: 'suggestion', label: '功能建议' },
  { value: 'data_loss', label: '数据风险' },
  { value: 'cloud', label: '云服务问题' },
  { value: 'ui', label: '界面体验' },
  { value: 'other', label: '其他' },
]

const MAX_ATTACHMENTS = 5
const MAX_ATTACHMENT_SIZE = 52_428_800 // 50 MB
const ALLOWED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'video/mp4',
  'video/webm',
  'video/quicktime',
]

const category = ref<FeedbackCategory>('bug')
const title = ref('')
const description = ref('')
const contactEmail = ref('')
const includeDiagnostics = ref(true)
const selectedFiles = ref<File[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

const isSubmitting = ref(false)
const submitStage = ref<'idle' | 'submitting' | 'uploading' | 'done'>('idle')
const errorMessage = ref('')
const successResult = ref<FeedbackSubmitResponse | null>(null)
const replies = ref<FeedbackReply[]>([])
const repliesLoading = ref(false)
const repliesLoaded = ref(false)

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return

  const newFiles = Array.from(input.files)
  const combined = [...selectedFiles.value, ...newFiles]

  if (combined.length > MAX_ATTACHMENTS) {
    errorMessage.value = `附件数量不能超过 ${MAX_ATTACHMENTS} 个。`
    return
  }

  for (const file of newFiles) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      errorMessage.value = `不支持的文件类型: ${file.name}。仅支持图片和视频。`
      return
    }
    if (file.size > MAX_ATTACHMENT_SIZE) {
      errorMessage.value = `文件 ${file.name} 超过大小限制 (50 MB)。`
      return
    }
  }

  selectedFiles.value = combined
  errorMessage.value = ''
  // Reset input so the same file can be re-selected
  input.value = ''
}

function removeFile(index: number) {
  selectedFiles.value = selectedFiles.value.filter((_, i) => i !== index)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function handleSubmit() {
  if (!title.value.trim()) {
    errorMessage.value = '请输入标题。'
    return
  }
  if (description.value.trim().length < 10) {
    errorMessage.value = '详细描述至少需要 10 个字符。'
    return
  }

  errorMessage.value = ''
  isSubmitting.value = true
  submitStage.value = 'submitting'

  try {
    const formData = new FormData()
    formData.append('category', category.value)
    formData.append('title', title.value.trim())
    formData.append('description', description.value.trim())
    if (contactEmail.value.trim()) {
      formData.append('contact_email', contactEmail.value.trim())
    }
    formData.append('include_diagnostics', String(includeDiagnostics.value))

    for (const file of selectedFiles.value) {
      formData.append('attachments', file)
    }

    if (selectedFiles.value.length > 0) {
      submitStage.value = 'uploading'
    }

    const result = await submitFeedback(formData)
    successResult.value = result
    submitStage.value = 'done'

    // Save feedback ID for future reply viewing
    try {
      const stored = JSON.parse(localStorage.getItem('zhangshu:feedback-ids') ?? '[]') as string[]
      if (!stored.includes(result.id)) {
        stored.push(result.id)
        localStorage.setItem('zhangshu:feedback-ids', JSON.stringify(stored.slice(-20)))
      }
    } catch {
      /* ignore */
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : '提交失败，请稍后重试。'
    // Strip technical details for user display
    errorMessage.value = msg.length > 200 ? msg.slice(0, 200) + '...' : msg
    submitStage.value = 'idle'
  } finally {
    isSubmitting.value = false
  }
}

function handleDone() {
  emit('close')
}

async function loadReplies() {
  if (!successResult.value || repliesLoaded.value) return
  repliesLoading.value = true
  try {
    const res = await listFeedbackReplies(successResult.value.id)
    replies.value = res.items
  } catch {
    /* ignore */
  } finally {
    repliesLoading.value = false
    repliesLoaded.value = true
  }
}

function formatReplyDate(d: string): string {
  try {
    return new Date(d).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return d
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="dialog-overlay" @click.self="emit('close')">
      <div class="dialog-panel feedback-dialog">
        <header class="dialog-header">
          <h2 class="dialog-title">提交反馈</h2>
          <button class="dialog-close-btn" type="button" @click="emit('close')">✕</button>
        </header>

        <!-- Success state -->
        <div v-if="successResult" class="dialog-body">
          <div class="success-message">
            <p class="success-icon">✓</p>
            <p>反馈已提交成功！</p>
            <p class="feedback-id">反馈编号: {{ successResult.id }}</p>
            <p v-if="successResult.uploaded_attachments > 0">
              已上传 {{ successResult.uploaded_attachments }} 个附件
            </p>
            <p v-if="successResult.failed_attachments > 0" class="warning-text">
              {{ successResult.failed_attachments }} 个附件上传失败，文字内容已保留。
            </p>
          </div>
          <div class="reply-section">
            <button
              v-if="!repliesLoaded"
              class="btn-secondary reply-toggle-btn"
              type="button"
              :disabled="repliesLoading"
              @click="loadReplies"
            >
              {{ repliesLoading ? '加载中...' : '查看管理员回复' }}
            </button>
            <div v-if="repliesLoaded" class="reply-list">
              <p v-if="!replies.length" class="no-replies">暂无回复</p>
              <div v-for="reply in replies" :key="reply.id" class="reply-item">
                <div class="reply-header">
                  <span class="reply-badge">{{ reply.author_type === 'admin' ? '管理员' : '系统' }}</span>
                  <span class="reply-time">{{ formatReplyDate(reply.created_at) }}</span>
                </div>
                <div class="reply-content">{{ reply.content }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Form state -->
        <div v-else class="dialog-body">
          <div class="form-group">
            <label for="fb-category">分类</label>
            <select id="fb-category" v-model="category">
              <option v-for="cat in CATEGORIES" :key="cat.value" :value="cat.value">
                {{ cat.label }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="fb-title">标题</label>
            <input
              id="fb-title"
              v-model="title"
              type="text"
              maxlength="120"
              placeholder="简要描述问题或建议"
            />
          </div>

          <div class="form-group">
            <label for="fb-desc">详细描述 <span class="required">*</span></label>
            <textarea
              id="fb-desc"
              v-model="description"
              rows="5"
              maxlength="5000"
              placeholder="请详细描述您遇到的问题或建议（至少 10 个字符）"
            />
            <span class="char-count">{{ description.length }} / 5000</span>
          </div>

          <div class="form-group">
            <label for="fb-email">联系邮箱（可选）</label>
            <input
              id="fb-email"
              v-model="contactEmail"
              type="email"
              placeholder="方便我们回复您"
            />
          </div>

          <div class="form-group">
            <label>附件（可选）</label>
            <div class="file-picker">
              <input
                ref="fileInputRef"
                type="file"
                multiple
                :accept="ALLOWED_TYPES.join(',')"
                @change="handleFileSelect"
              />
              <button
                v-if="selectedFiles.length < MAX_ATTACHMENTS"
                class="btn-add-file"
                type="button"
                @click="fileInputRef?.click()"
              >
                + 添加图片/视频
              </button>
            </div>
            <p class="file-hint">
              支持图片 (PNG/JPEG/WebP/GIF) 和视频 (MP4/WebP/MOV)，单个最大 50 MB，最多
              {{ MAX_ATTACHMENTS }} 个。
            </p>
            <ul v-if="selectedFiles.length > 0" class="file-list">
              <li v-for="(file, idx) in selectedFiles" :key="idx" class="file-item">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatSize(file.size) }}</span>
                <button class="file-remove-btn" type="button" @click="removeFile(idx)">✕</button>
              </li>
            </ul>
          </div>

          <div class="form-group checkbox-group">
            <label>
              <input v-model="includeDiagnostics" type="checkbox" />
              附带基础诊断信息（应用版本、平台，不含正文和日志）
            </label>
          </div>

          <div class="privacy-notice">
            <p>
              ⚠
              图片和视频可能包含作品内容或个人信息，请确认后提交。不会自动上传本地日志、数据库或正文内容。
            </p>
          </div>

          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        </div>

        <footer class="dialog-footer">
          <button
            v-if="!successResult"
            class="btn-secondary"
            type="button"
            :disabled="isSubmitting"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            v-if="!successResult"
            class="btn-primary"
            type="button"
            :disabled="isSubmitting"
            @click="handleSubmit"
          >
            <template v-if="submitStage === 'submitting'">正在提交…</template>
            <template v-else-if="submitStage === 'uploading'">正在上传附件…</template>
            <template v-else>提交反馈</template>
          </button>
          <button v-if="successResult" class="btn-primary" type="button" @click="handleDone">
            完成
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
}

.feedback-dialog {
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: var(--zs-color-surface, #fff);
  border-radius: var(--zs-radius-lg, 8px);
  box-shadow: var(--zs-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.15));
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--zs-space-4, 16px);
  border-bottom: 1px solid var(--zs-color-border, #ddd);
}

.dialog-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.dialog-close-btn {
  border: none;
  background: transparent;
  font-size: 1.25rem;
  cursor: pointer;
  opacity: 0.5;
  color: inherit;
}

.dialog-close-btn:hover {
  opacity: 1;
}

.dialog-body {
  padding: var(--zs-space-4, 16px);
  overflow-y: auto;
  flex: 1;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--zs-space-2, 8px);
  padding: var(--zs-space-3, 12px) var(--zs-space-4, 16px);
  border-top: 1px solid var(--zs-color-border, #ddd);
}

.form-group {
  margin-bottom: var(--zs-space-3, 12px);
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 4px;
}

.required {
  color: var(--zs-color-danger, #ef4444);
}

.form-group input[type='text'],
.form-group input[type='email'],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: var(--zs-color-surface, #fff);
  color: inherit;
  font-size: 0.875rem;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
}

.char-count {
  display: block;
  text-align: right;
  font-size: 0.75rem;
  opacity: 0.5;
  margin-top: 2px;
}

.file-picker input[type='file'] {
  display: none;
}

.btn-add-file {
  padding: 4px 12px;
  font-size: 0.8125rem;
  border: 1px dashed var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: transparent;
  cursor: pointer;
  color: inherit;
}

.btn-add-file:hover {
  background: var(--zs-color-surface-hover, #f5f5f5);
}

.file-hint {
  font-size: 0.75rem;
  opacity: 0.5;
  margin-top: 4px;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  margin-bottom: 4px;
  font-size: 0.8125rem;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  flex-shrink: 0;
  opacity: 0.5;
}

.file-remove-btn {
  flex-shrink: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0.5;
  color: inherit;
}

.file-remove-btn:hover {
  opacity: 1;
  color: var(--zs-color-danger, #ef4444);
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 400;
  cursor: pointer;
}

.privacy-notice {
  padding: 8px 12px;
  border-radius: var(--zs-radius-sm, 4px);
  background: var(--zs-color-warning-bg, #fffbeb);
  font-size: 0.8125rem;
  margin-top: 8px;
}

.privacy-notice p {
  margin: 0;
}

.error-message {
  color: var(--zs-color-danger, #ef4444);
  font-size: 0.875rem;
  margin-top: 8px;
}

.success-message {
  text-align: center;
  padding: 24px 0;
}

.success-icon {
  font-size: 3rem;
  color: var(--zs-color-success, #22c55e);
  margin: 0 0 8px;
}

.feedback-id {
  font-family: monospace;
  font-size: 0.8125rem;
  opacity: 0.6;
  margin-top: 8px;
}

.warning-text {
  color: var(--zs-color-warning, #f59e0b);
  font-size: 0.875rem;
}

.reply-section {
  margin-top: 16px;
  border-top: 1px solid var(--zs-color-border, #ddd);
  padding-top: 16px;
}

.reply-toggle-btn {
  width: 100%;
  text-align: center;
}

.reply-list {
  max-height: 240px;
  overflow-y: auto;
}

.no-replies {
  text-align: center;
  font-size: 0.875rem;
  opacity: 0.5;
  margin: 8px 0;
}

.reply-item {
  padding: 8px 12px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  margin-bottom: 8px;
}

.reply-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 0.75rem;
}

.reply-badge {
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--zs-color-primary, #3b82f6);
  color: #fff;
  font-size: 0.6875rem;
}

.reply-time {
  opacity: 0.5;
  margin-left: auto;
}

.reply-content {
  white-space: pre-wrap;
  line-height: 1.5;
  font-size: 0.8125rem;
}

.btn-secondary {
  padding: 8px 20px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: transparent;
  cursor: pointer;
  color: inherit;
  font-size: 0.875rem;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--zs-color-surface-hover, #f5f5f5);
}

.btn-primary {
  padding: 8px 20px;
  border: none;
  border-radius: var(--zs-radius-sm, 4px);
  background: var(--zs-color-primary, #3b82f6);
  color: #fff;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

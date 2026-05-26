<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { confirmKnowledgeImport, previewKnowledgeImport } from '@/entities/knowledge/api'
import type {
  KnowledgeCredibility,
  KnowledgeImportPreview,
  KnowledgeImportResult,
  KnowledgeSourceType,
} from '@/entities/knowledge/types'
import { knowledgeCredibilityLabels, knowledgeSourceTypeLabels } from '@/entities/knowledge/types'

const props = defineProps<{
  projectId: string
}>()

const emit = defineEmits<{
  close: []
  imported: []
}>()

type ImportStep = 'select' | 'preview' | 'importing' | 'result'

const step = ref<ImportStep>('select')
const selectedFiles = ref<File[]>([])
const preview = ref<KnowledgeImportPreview | null>(null)
const result = ref<KnowledgeImportResult | null>(null)
const errorMessage = ref('')
const isProcessing = ref(false)

const options = reactive({
  sourceType: 'file' as KnowledgeSourceType,
  credibility: 'normal' as KnowledgeCredibility,
  tags: '',
})

const ACCEPTED_TYPES = '.txt,.md,.docx,.doc,.pdf,.zip'

const sourceTypeOptions: { value: KnowledgeSourceType; label: string }[] = [
  { value: 'file', label: knowledgeSourceTypeLabels.file },
  { value: 'note', label: knowledgeSourceTypeLabels.note },
  { value: 'book', label: knowledgeSourceTypeLabels.book },
  { value: 'webpage', label: knowledgeSourceTypeLabels.webpage },
  { value: 'quote', label: knowledgeSourceTypeLabels.quote },
  { value: 'custom', label: knowledgeSourceTypeLabels.custom },
]

const credibilityOptions: { value: KnowledgeCredibility; label: string }[] = [
  { value: 'low', label: knowledgeCredibilityLabels.low },
  { value: 'normal', label: knowledgeCredibilityLabels.normal },
  { value: 'high', label: knowledgeCredibilityLabels.high },
]

const supportedFileCount = computed(() => {
  const supported = new Set(['.txt', '.md', '.docx', '.doc', '.pdf'])
  return selectedFiles.value.filter((file) => {
    const ext = getExtension(file.name)
    return supported.has(ext) || ext === '.zip'
  }).length
})

const totalFileSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
})

function getExtension(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

function getDisplayName(file: File): string {
  return file.webkitRelativePath || file.name
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getExtensionLabel(ext: string): string {
  const labels: Record<string, string> = {
    '.txt': '文本',
    '.md': 'Markdown',
    '.docx': 'Word',
    '.doc': '旧版 Word',
    '.pdf': 'PDF',
    '.zip': '压缩包',
  }
  return labels[ext] || ext
}

const canPreview = computed(() => selectedFiles.value.length > 0)
const canImport = computed(() => preview.value?.can_import ?? false)

const fileInput = ref<HTMLInputElement | null>(null)
const folderInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  if (folderInput.value) {
    folderInput.value.setAttribute('webkitdirectory', '')
  }
})

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return

  const newFiles = Array.from(input.files)
  selectedFiles.value = [...selectedFiles.value, ...newFiles]
  input.value = ''
}

function handleFolderSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return

  const newFiles = Array.from(input.files)
  selectedFiles.value = [...selectedFiles.value, ...newFiles]
  input.value = ''
}

function handleRemoveFile(index: number) {
  selectedFiles.value = selectedFiles.value.filter((_, i) => i !== index)
  preview.value = null
}

function handleClearFiles() {
  selectedFiles.value = []
  preview.value = null
}

async function handlePreview() {
  if (!canPreview.value) return

  isProcessing.value = true
  errorMessage.value = ''

  try {
    preview.value = await previewKnowledgeImport(props.projectId, selectedFiles.value)
    step.value = 'preview'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '预览失败，请稍后重试。'
  } finally {
    isProcessing.value = false
  }
}

async function handleConfirmImport() {
  if (!canImport.value) return

  step.value = 'importing'
  isProcessing.value = true
  errorMessage.value = ''

  try {
    result.value = await confirmKnowledgeImport(props.projectId, selectedFiles.value, {
      sourceType: options.sourceType,
      credibility: options.credibility,
      tags: options.tags,
    })
    step.value = 'result'
    emit('imported')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导入失败，请稍后重试。'
    step.value = 'preview'
  } finally {
    isProcessing.value = false
  }
}

function handleBackToSelect() {
  step.value = 'select'
  preview.value = null
}
</script>

<template>
  <div class="zs-dialog" role="presentation" @click.self="emit('close')">
    <section
      class="zs-dialog-content import-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="knowledge-import-title"
    >
      <header class="zs-dialog-header">
        <h2 id="knowledge-import-title">批量导入知识资料</h2>
        <button
          class="zs-icon-button"
          type="button"
          aria-label="关闭"
          @click="emit('close')"
        >
          x
        </button>
      </header>

      <div class="import-body">
        <p class="helper-note">
          支持批量导入文件或选择文件夹。每个文件会生成一条知识资料，并自动分块。支持
          .txt、.md、.docx、.doc、.pdf 格式，也支持 .zip 压缩包。
        </p>

        <section v-if="errorMessage" class="error-banner" role="alert">
          {{ errorMessage }}
        </section>

        <!-- Step 1: Select files -->
        <div v-if="step === 'select'" class="step-select">
          <div class="input-buttons">
            <button
              class="zs-button zs-button-primary"
              type="button"
              @click="fileInput?.click()"
            >
              选择文件
            </button>
            <input
              ref="fileInput"
              type="file"
              multiple
              :accept="ACCEPTED_TYPES"
              style="display: none"
              @change="handleFileSelect"
            />
            <button
              class="zs-button zs-button-secondary"
              type="button"
              @click="folderInput?.click()"
            >
              选择文件夹
            </button>
            <input
              ref="folderInput"
              type="file"
              multiple
              :accept="ACCEPTED_TYPES"
              style="display: none"
              @change="handleFolderSelect"
            />
          </div>

          <div v-if="selectedFiles.length === 0" class="empty-files">
            <p>尚未选择文件。点击上方按钮添加文件。</p>
            <p class="empty-files-hint">支持 .txt、.md、.docx、.doc、.pdf 和 .zip 格式</p>
          </div>

          <template v-else>
            <div class="file-summary">
              已选择 <strong>{{ selectedFiles.length }}</strong> 个文件（{{ formatSize(totalFileSize) }}），
              预计导入 <strong>{{ supportedFileCount }}</strong> 个支持的文件
            </div>

            <ul class="file-list">
              <li v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                <span class="file-name" :title="getDisplayName(file)">
                  {{ getDisplayName(file) }}
                </span>
                <span class="file-ext-label">{{ getExtensionLabel(getExtension(file.name)) }}</span>
                <span class="file-size">{{ formatSize(file.size) }}</span>
                <button
                  class="zs-button-ghost file-remove"
                  type="button"
                  @click="handleRemoveFile(index)"
                >
                  移除
                </button>
              </li>
            </ul>
          </template>

          <div v-if="selectedFiles.length > 0" class="step-actions">
            <button class="zs-button zs-button-secondary" type="button" @click="handleClearFiles">
              清空
            </button>
            <button
              class="zs-button zs-button-primary"
              type="button"
              :disabled="!canPreview || isProcessing"
              @click="handlePreview"
            >
              {{ isProcessing ? '正在预览...' : '预览导入' }}
            </button>
          </div>
        </div>

        <!-- Step 2: Preview -->
        <div v-else-if="step === 'preview' && preview" class="step-preview">
          <div class="preview-summary">
            <p>
              <strong>{{ preview.supported_count }}</strong> 个文件可导入，
              共 <strong>{{ preview.total_word_count }}</strong> 字。
            </p>
            <p v-if="preview.unsupported_count > 0" class="preview-unsupported-note">
              {{ preview.unsupported_count }} 个文件格式不支持，已跳过。
            </p>
            <p v-if="preview.empty_files.length > 0" class="preview-empty-note">
              {{ preview.empty_files.length }} 个文件为空，已跳过。
            </p>
            <p v-if="preview.failed_files.length > 0" class="preview-failed-note">
              {{ preview.failed_files.length }} 个文件解析失败。
            </p>
          </div>

          <div v-if="preview.unsupported_files.length > 0" class="unsupported-section">
            <p class="unsupported-title">不支持的文件：</p>
            <ul class="unsupported-list">
              <li v-for="(name, i) in preview.unsupported_files" :key="i" class="unsupported-item">
                <span class="unsupported-name" :title="name">{{ name }}</span>
                <span v-if="getExtension(name) === '.pdf'" class="unsupported-hint">
                  扫描版 PDF 可能无法提取文字。
                </span>
              </li>
            </ul>
          </div>

          <div v-if="preview.warnings.length > 0" class="preview-warnings">
            <p class="warning-title">警告：</p>
            <ul>
              <li v-for="(warning, i) in preview.warnings" :key="i">{{ warning }}</li>
            </ul>
          </div>

          <ul class="preview-documents">
            <li v-for="doc in preview.documents" :key="doc.relative_path" class="preview-doc">
              <span class="doc-title" :title="doc.relative_path">{{ doc.title }}</span>
              <span class="doc-path" :title="doc.relative_path">{{ doc.relative_path }}</span>
              <span class="doc-meta">{{ doc.word_count }} 字 · {{ formatSize(doc.size) }}</span>
            </li>
          </ul>

          <div class="import-options">
            <h3>导入选项</h3>
            <label class="zs-field">
              <span class="zs-field-label">资料类型</span>
              <select v-model="options.sourceType">
                <option v-for="opt in sourceTypeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="zs-field">
              <span class="zs-field-label">可信度</span>
              <select v-model="options.credibility">
                <option v-for="opt in credibilityOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="zs-field">
              <span class="zs-field-label">标签（可选）</span>
              <input v-model="options.tags" type="text" placeholder="多个标签用逗号分隔" />
            </label>
          </div>

          <div class="step-actions">
            <button class="zs-button zs-button-secondary" type="button" @click="handleBackToSelect">
              返回
            </button>
            <button
              class="zs-button zs-button-primary"
              type="button"
              :disabled="!canImport || isProcessing"
              @click="handleConfirmImport"
            >
              {{ isProcessing ? '正在导入...' : '确认导入' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Importing -->
        <div v-else-if="step === 'importing'" class="step-importing">
          <p class="importing-message">正在导入知识资料，请稍候...</p>
        </div>

        <!-- Step 4: Result -->
        <div v-else-if="step === 'result' && result" class="step-result">
          <div class="result-success">
            <p>
              成功导入 <strong>{{ result.imported_count }}</strong> 个知识资料。
            </p>
          </div>

          <div v-if="result.unsupported_files.length > 0" class="result-unsupported">
            <p class="warning-title">未支持的文件（{{ result.unsupported_files.length }}）：</p>
            <ul>
              <li v-for="(name, i) in result.unsupported_files" :key="i">{{ name }}</li>
            </ul>
          </div>

          <div v-if="result.failed_files.length > 0" class="result-failed">
            <p class="warning-title">解析失败的文件（{{ result.failed_files.length }}）：</p>
            <ul>
              <li v-for="(name, i) in result.failed_files" :key="i">{{ name }}</li>
            </ul>
          </div>

          <div v-if="result.warnings.length > 0" class="result-warnings">
            <p class="warning-title">警告：</p>
            <ul>
              <li v-for="(warning, i) in result.warnings" :key="i">{{ warning }}</li>
            </ul>
          </div>

          <ul class="result-sources">
            <li v-for="source in result.imported_sources" :key="source.id" class="result-source">
              <span class="source-title">{{ source.title }}</span>
              <span class="source-meta">
                {{ knowledgeSourceTypeLabels[source.source_type] || source.source_type }}
                · {{ source.chunk_count }} 个分块
              </span>
            </li>
          </ul>

          <div class="step-actions">
            <button class="zs-button zs-button-primary" type="button" @click="emit('close')">
              完成
            </button>
          </div>
        </div>
      </div>

      <footer class="zs-dialog-footer">
        <button class="zs-button zs-button-secondary" type="button" @click="emit('close')">
          取消
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.import-dialog {
  max-width: min(640px, 90vw);
  width: min(640px, 90vw);
  margin-inline: auto;
}

.import-body {
  padding: var(--zs-space-5) var(--zs-space-6);
  display: grid;
  gap: var(--zs-space-4);
}

.helper-note {
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  margin: 0;
  line-height: 1.7;
}

.error-banner {
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-danger);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.82rem;
}

.input-buttons {
  display: flex;
  gap: var(--zs-space-3);
  flex-wrap: wrap;
}

.empty-files {
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  padding: var(--zs-space-6) 0;
  text-align: center;
}

.empty-files p {
  margin: 0 0 var(--zs-space-1);
}

.empty-files-hint {
  font-size: 0.78rem;
  color: var(--zs-color-text-faint);
}

.file-summary {
  background: var(--zs-color-info-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.84rem;
  line-height: 1.6;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-1);
  max-height: 220px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  font-size: 0.82rem;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-ext-label {
  color: var(--zs-color-info);
  background: var(--zs-color-info-soft);
  border-radius: var(--zs-radius-pill);
  padding: 1px 6px;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

.file-size {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
  white-space: nowrap;
}

.file-remove {
  color: var(--zs-color-danger);
  font-size: 0.76rem;
  padding: 0 var(--zs-space-2);
  min-height: auto;
}

.step-actions {
  display: flex;
  gap: var(--zs-space-2);
  justify-content: flex-end;
  padding-top: var(--zs-space-3);
  border-top: 1px solid var(--zs-color-border-soft);
}

.preview-summary {
  background: var(--zs-color-info-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.84rem;
}

.preview-summary p {
  margin: 0 0 var(--zs-space-1);
}

.preview-summary p:last-child {
  margin-bottom: 0;
}

.preview-unsupported-note {
  color: var(--zs-color-warning);
}

.preview-empty-note,
.preview-failed-note {
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
}

.unsupported-section {
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.82rem;
}

.unsupported-title {
  font-weight: 700;
  margin: 0 0 var(--zs-space-1);
}

.unsupported-list {
  margin: 0;
  padding-left: var(--zs-space-5);
}

.unsupported-item {
  margin-bottom: var(--zs-space-1);
}

.unsupported-name {
  font-weight: 600;
}

.unsupported-hint {
  display: block;
  font-size: 0.76rem;
  color: var(--zs-color-text-muted);
  margin-top: 1px;
}

.preview-warnings,
.result-warnings {
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.82rem;
}

.warning-title {
  font-weight: 700;
  margin: 0 0 var(--zs-space-1);
}

.preview-warnings ul,
.result-warnings ul {
  margin: 0;
  padding-left: var(--zs-space-5);
}

.result-unsupported,
.result-failed {
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.82rem;
}

.result-unsupported ul,
.result-failed ul {
  margin: 0;
  padding-left: var(--zs-space-5);
}

.preview-documents,
.result-sources {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-1);
  max-height: 220px;
  overflow-y: auto;
}

.preview-doc,
.result-source {
  display: grid;
  gap: 2px;
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  font-size: 0.82rem;
}

.doc-title,
.source-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.doc-path {
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta,
.source-meta {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
}

.import-options {
  display: grid;
  gap: var(--zs-space-3);
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-4);
}

.import-options h3 {
  margin: 0;
  font-size: 0.9rem;
}

.import-options .zs-field {
  display: grid;
  gap: var(--zs-space-1);
}

.import-options .zs-field .zs-field-label {
  font-size: 0.78rem;
  color: var(--zs-color-text-muted);
  font-weight: 700;
}

.import-options .zs-field select,
.import-options .zs-field input {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2) var(--zs-space-3);
  font-size: 0.84rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.step-importing {
  text-align: center;
  padding: var(--zs-space-8) 0;
}

.importing-message {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.result-success {
  background: var(--zs-color-success-soft);
  border: 1px solid var(--zs-color-success);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3) var(--zs-space-4);
  font-size: 0.84rem;
}

.result-success p {
  margin: 0;
}

.step-select,
.step-preview,
.step-result {
  display: grid;
  gap: var(--zs-space-4);
}
</style>

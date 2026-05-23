<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

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

const ACCEPTED_TYPES = '.txt,.md,.docx'

const sourceTypeOptions: { value: KnowledgeSourceType; label: string }[] = [
  { value: 'file', label: knowledgeSourceTypeLabels.file },
  { value: 'book', label: knowledgeSourceTypeLabels.book },
  { value: 'webpage', label: knowledgeSourceTypeLabels.webpage },
  { value: 'note', label: knowledgeSourceTypeLabels.note },
  { value: 'quote', label: knowledgeSourceTypeLabels.quote },
  { value: 'custom', label: knowledgeSourceTypeLabels.custom },
]

const credibilityOptions: { value: KnowledgeCredibility; label: string }[] = [
  { value: 'low', label: knowledgeCredibilityLabels.low },
  { value: 'normal', label: knowledgeCredibilityLabels.normal },
  { value: 'high', label: knowledgeCredibilityLabels.high },
]

const canPreview = computed(() => selectedFiles.value.length > 0)
const canImport = computed(() => preview.value?.can_import ?? false)

function handleFileSelect(event: Event) {
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
  <div class="zs-dialog" role="presentation">
    <section
      class="zs-dialog-content import-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="knowledge-import-title"
    >
      <header class="zs-dialog-header">
        <h2 id="knowledge-import-title">导入知识资料</h2>
        <button
          class="zs-icon-button"
          type="button"
          aria-label="关闭"
          @click="emit('close')"
        >
          x
        </button>
      </header>

      <div class="dialog-body">
        <p class="helper-note">
          支持导入 .txt、.md、.docx 文件。导入后会自动生成知识资料和分块。
        </p>

        <section v-if="errorMessage" class="error-banner" role="alert">
          {{ errorMessage }}
        </section>

        <!-- Step 1: Select files -->
        <div v-if="step === 'select'" class="step-select">
          <label class="file-input-wrapper">
            <input
              type="file"
              multiple
              :accept="ACCEPTED_TYPES"
              @change="handleFileSelect"
            />
            <span class="file-input-button">选择文件</span>
          </label>

          <div v-if="selectedFiles.length === 0" class="empty-files">
            <p>尚未选择文件。点击"选择文件"添加 .txt、.md 或 .docx 文件。</p>
          </div>

          <ul v-else class="file-list">
            <li v-for="(file, index) in selectedFiles" :key="index" class="file-item">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</span>
              <button
                class="file-remove"
                type="button"
                @click="handleRemoveFile(index)"
              >
                移除
              </button>
            </li>
          </ul>

          <div v-if="selectedFiles.length > 0" class="select-actions">
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
              <strong>{{ preview.document_count }}</strong> 个文件可导入，
              共 <strong>{{ preview.total_word_count }}</strong> 字。
            </p>
          </div>

          <div v-if="preview.warnings.length > 0" class="preview-warnings">
            <p class="warning-title">警告：</p>
            <ul>
              <li v-for="(warning, i) in preview.warnings" :key="i">{{ warning }}</li>
            </ul>
          </div>

          <ul class="preview-documents">
            <li v-for="doc in preview.documents" :key="doc.filename" class="preview-doc">
              <span class="doc-title">{{ doc.title }}</span>
              <span class="doc-meta">{{ doc.word_count }} 字</span>
            </li>
          </ul>

          <div class="import-options">
            <h3>导入选项</h3>
            <label class="zs-field">
              <span>资料类型</span>
              <select v-model="options.sourceType">
                <option v-for="opt in sourceTypeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="zs-field">
              <span>可信度</span>
              <select v-model="options.credibility">
                <option v-for="opt in credibilityOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="zs-field">
              <span>标签（可选）</span>
              <input v-model="options.tags" type="text" placeholder="多个标签用逗号分隔" />
            </label>
          </div>

          <div class="preview-actions">
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

          <div class="result-actions">
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
  width: min(600px, 90vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px;
  display: grid;
  gap: 12px;
}

.helper-note {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  margin: 0;
}

.error-banner {
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  border-radius: 6px;
  color: var(--zs-color-danger);
  padding: 8px 12px;
  font-size: 0.82rem;
}

.file-input-wrapper {
  display: inline-block;
}

.file-input-wrapper input[type='file'] {
  display: none;
}

.file-input-button {
  display: inline-block;
  padding: 6px 14px;
  border: 1px solid var(--zs-color-primary);
  border-radius: 6px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-size: 0.84rem;
  font-weight: 700;
  cursor: pointer;
}

.file-input-button:hover {
  opacity: 0.9;
}

.empty-files {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  padding: 16px 0;
  text-align: center;
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  font-size: 0.82rem;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
}

.file-remove {
  border: none;
  background: transparent;
  color: var(--zs-color-danger);
  font-size: 0.76rem;
  cursor: pointer;
  padding: 0;
}

.file-remove:hover {
  text-decoration: underline;
}

.select-actions,
.preview-actions,
.result-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 8px;
}

.preview-summary {
  background: var(--zs-color-info-soft);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 0.84rem;
}

.preview-summary p {
  margin: 0;
}

.preview-warnings,
.result-warnings {
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 0.82rem;
}

.warning-title {
  font-weight: 700;
  margin: 0 0 4px;
}

.preview-warnings ul,
.result-warnings ul {
  margin: 0;
  padding-left: 18px;
}

.preview-documents,
.result-sources {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.preview-doc,
.result-source {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  border-radius: 6px;
  font-size: 0.82rem;
}

.doc-title,
.source-title {
  flex: 1;
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
  gap: 8px;
  border-top: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  padding-top: 12px;
}

.import-options h3 {
  margin: 0;
  font-size: 0.9rem;
}

.zs-field {
  display: grid;
  gap: 3px;
}

.zs-field span {
  font-size: 0.76rem;
  color: var(--zs-color-text-muted);
  font-weight: 700;
}

.zs-field select,
.zs-field input {
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.82rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.step-importing {
  text-align: center;
  padding: 40px 0;
}

.importing-message {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.result-success {
  background: var(--zs-color-success-soft, #f0fdf4);
  border: 1px solid var(--zs-color-success, #22c55e);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 0.84rem;
}

.result-success p {
  margin: 0;
}

.zs-dialog-footer {
  border-top: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  padding: 12px 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

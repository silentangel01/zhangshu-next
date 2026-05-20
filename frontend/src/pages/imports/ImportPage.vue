<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { confirmImport, previewImport } from '@/entities/import/api'
import type { ImportPreview, ImportReport, ImportType } from '@/entities/import/types'
import ImportPreviewPanel from '@/features/imports/ImportPreviewPanel.vue'
import ImportReportPanel from '@/features/imports/ImportReportPanel.vue'

const importType = ref<ImportType>('legacy_json')
const selectedFile = ref<File | null>(null)
const preview = ref<ImportPreview | null>(null)
const report = ref<ImportReport | null>(null)
const projectTitleOverride = ref('')
const isPreviewing = ref(false)
const isConfirming = ref(false)
const errorMessage = ref('')

const acceptedFileTypes = computed(() => (importType.value === 'legacy_json' ? '.json' : '.zip'))
const selectedTypeLabel = computed(() =>
  importType.value === 'legacy_json' ? '旧版 JSON' : '文件夹压缩包',
)

function handleTypeChange() {
  selectedFile.value = null
  preview.value = null
  report.value = null
  projectTitleOverride.value = ''
  errorMessage.value = ''
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  preview.value = null
  report.value = null
  projectTitleOverride.value = ''
  errorMessage.value = ''
}

async function handlePreview() {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择要导入的文件。'
    return
  }

  isPreviewing.value = true
  errorMessage.value = ''
  report.value = null

  try {
    const result = await previewImport(selectedFile.value, importType.value)
    preview.value = result
    projectTitleOverride.value = result.detected_project_title
  } catch (error) {
    preview.value = null
    errorMessage.value = getErrorMessage(error, '解析失败，请检查文件格式或编码。')
  } finally {
    isPreviewing.value = false
  }
}

async function handleConfirm() {
  if (!preview.value) {
    return
  }

  isConfirming.value = true
  errorMessage.value = ''

  try {
    report.value = await confirmImport(preview.value.import_id, {
      mode: 'create_project',
      project_title: projectTitleOverride.value.trim() || null,
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '导入失败，请稍后重试。')
  } finally {
    isConfirming.value = false
  }
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="import-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">掌书 Next</p>
        <h1>导入作品</h1>
      </div>
      <RouterLink class="secondary-link" to="/projects">返回项目</RouterLink>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section class="import-card">
      <div class="field-group">
        <span class="field-label">导入类型</span>
        <div class="segmented-control" role="radiogroup" aria-label="导入类型">
          <label>
            <input
              v-model="importType"
              type="radio"
              value="legacy_json"
              @change="handleTypeChange"
            />
            <span>旧版 JSON</span>
          </label>
          <label>
            <input
              v-model="importType"
              type="radio"
              value="folder_zip"
              @change="handleTypeChange"
            />
            <span>文件夹压缩包</span>
          </label>
        </div>
      </div>

      <label class="file-field">
        <span>{{ selectedTypeLabel }}文件</span>
        <input :accept="acceptedFileTypes" type="file" @change="handleFileChange" />
      </label>

      <div class="actions-row">
        <button
          class="primary-button"
          type="button"
          :disabled="isPreviewing || !selectedFile"
          @click="handlePreview"
        >
          {{ isPreviewing ? '正在解析……' : '预览导入' }}
        </button>
        <p v-if="selectedFile" class="file-note">
          已选择：{{ selectedFile.name }}
        </p>
      </div>
    </section>

    <section v-if="isPreviewing" class="state-panel" aria-live="polite">
      正在解析……
    </section>

    <ImportPreviewPanel
      v-if="preview"
      v-model:project-title="projectTitleOverride"
      :preview="preview"
      :is-confirming="isConfirming"
      @confirm="handleConfirm"
    />

    <ImportReportPanel v-if="report" :report="report" />
  </main>
</template>

<style scoped>
.import-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 40px;
  background: #f6f8fb;
  color: #111827;
}

.page-header,
.import-card,
.state-panel,
.error-banner,
.preview-panel,
.report-panel {
  max-width: 980px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.1;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 14px;
  background: #ffffff;
  color: #374151;
  font-weight: 800;
  text-decoration: none;
}

.error-banner {
  box-sizing: border-box;
  margin-bottom: 16px;
  border: 1px solid #f4b4ad;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff1f0;
  color: #9f1c12;
  font-weight: 700;
}

.import-card,
.state-panel {
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
}

.import-card {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
  padding: 22px;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.field-group,
.file-field {
  display: grid;
  gap: 8px;
}

.field-label,
.file-field span {
  color: #4b5563;
  font-weight: 800;
}

.segmented-control {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.segmented-control label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fbfcfe;
  color: #374151;
  font-weight: 800;
}

input[type='file'] {
  width: 100%;
  box-sizing: border-box;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
  color: #374151;
  font: inherit;
}

.actions-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.file-note {
  margin: 0;
  color: #64748b;
  overflow-wrap: anywhere;
}

.state-panel {
  display: grid;
  place-items: center;
  min-height: 120px;
  margin-bottom: 18px;
  color: #64748b;
  font-weight: 800;
}

.preview-panel,
.report-panel {
  margin-top: 18px;
}

button {
  min-height: 38px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}

@media (max-width: 720px) {
  .import-page {
    padding: 24px 16px;
  }

  .page-header,
  .actions-row {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button,
  .secondary-link {
    justify-content: center;
    width: 100%;
  }
}
</style>

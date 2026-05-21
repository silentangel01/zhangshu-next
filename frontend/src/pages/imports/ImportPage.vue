<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { commitProjectImport, previewProjectImport } from '@/entities/import/api'
import type { ImportPreview, ImportReport } from '@/entities/import/types'
import { listProjects } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import ImportPreviewPanel from '@/features/imports/ImportPreviewPanel.vue'
import ImportReportPanel from '@/features/imports/ImportReportPanel.vue'

const selectedFiles = ref<File[]>([])
const preview = ref<ImportPreview | null>(null)
const report = ref<ImportReport | null>(null)
const projects = ref<Project[]>([])
const importMode = ref<'create_project' | 'append_project'>('create_project')
const selectedProjectId = ref('')
const projectTitleOverride = ref('')
const isPreviewing = ref(false)
const isConfirming = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const selectedFileLabel = computed(() => {
  if (selectedFiles.value.length === 0) {
    return ''
  }
  if (selectedFiles.value.length === 1) {
    return selectedFiles.value[0]?.name ?? ''
  }
  return `${selectedFiles.value.length} 个文件`
})

onMounted(() => {
  void loadProjects()
})

async function loadProjects() {
  try {
    projects.value = await listProjects()
    selectedProjectId.value = projects.value[0]?.id ?? ''
  } catch {
    projects.value = []
  }
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFiles.value = Array.from(input.files ?? [])
  preview.value = null
  report.value = null
  projectTitleOverride.value = ''
  errorMessage.value = ''
  successMessage.value = ''
}

async function handlePreview() {
  if (selectedFiles.value.length === 0) {
    errorMessage.value = '请先选择文件夹或文件。'
    return
  }

  isPreviewing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  report.value = null

  try {
    const result = await previewProjectImport(selectedFiles.value)
    preview.value = result
    projectTitleOverride.value = result.detected_project_title
  } catch (error) {
    preview.value = null
    errorMessage.value = getErrorMessage(error, '导入失败，请检查文件')
  } finally {
    isPreviewing.value = false
  }
}

function handleCancelPreview() {
  preview.value = null
  report.value = null
  successMessage.value = ''
  errorMessage.value = ''
}

async function handleConfirm() {
  if (!preview.value) {
    return
  }
  if (importMode.value === 'append_project' && !selectedProjectId.value) {
    errorMessage.value = '请先选择要导入的项目。'
    return
  }

  isConfirming.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    report.value = await commitProjectImport({
      import_id: preview.value.import_id,
      mode: importMode.value,
      project_id: importMode.value === 'append_project' ? selectedProjectId.value : null,
      project_title: importMode.value === 'create_project'
        ? projectTitleOverride.value.trim() || null
        : null,
    })
    successMessage.value = '导入成功'
    await loadProjects()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '导入失败，请检查文件')
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
        <p class="eyebrow">章枢 Next</p>
        <h1>导入作品</h1>
      </div>
      <RouterLink class="secondary-link" to="/projects">返回项目</RouterLink>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>
    <section v-if="successMessage" class="success-banner" role="status">
      {{ successMessage }}
    </section>

    <section class="import-card">
      <p class="safe-note">预览阶段不会写入正式项目</p>

      <label class="file-field">
        <span>选择文件夹</span>
        <input
          type="file"
          multiple
          webkitdirectory
          @change="handleFileChange"
        />
      </label>

      <label class="file-field">
        <span>选择文件</span>
        <input
          type="file"
          multiple
          accept=".txt,.md,.docx"
          @change="handleFileChange"
        />
      </label>

      <div class="actions-row">
        <button
          class="primary-button"
          type="button"
          :disabled="isPreviewing || selectedFiles.length === 0"
          @click="handlePreview"
        >
          {{ isPreviewing ? '正在预览…' : '预览导入' }}
        </button>
        <button v-if="preview" class="secondary-button" type="button" @click="handleCancelPreview">
          取消
        </button>
        <p v-if="selectedFileLabel" class="file-note">已选择：{{ selectedFileLabel }}</p>
      </div>
    </section>

    <section v-if="isPreviewing" class="state-panel" aria-live="polite">
      正在解析…
    </section>

    <section v-if="preview" class="commit-card">
      <div class="field-group">
        <span class="field-label">导入方式</span>
        <div class="segmented-control" role="radiogroup" aria-label="导入方式">
          <label>
            <input v-model="importMode" type="radio" value="create_project" />
            <span>创建新项目</span>
          </label>
          <label>
            <input v-model="importMode" type="radio" value="append_project" />
            <span>导入到已有项目</span>
          </label>
        </div>
      </div>

      <label v-if="importMode === 'append_project'" class="field-group">
        <span class="field-label">目标项目</span>
        <select v-model="selectedProjectId">
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.title }}
          </option>
        </select>
      </label>
    </section>

    <ImportPreviewPanel
      v-if="preview"
      v-model:project-title="projectTitleOverride"
      :preview="preview"
      :is-confirming="isConfirming"
      :show-project-title="importMode === 'create_project'"
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
.commit-card,
.state-panel,
.error-banner,
.success-banner,
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

.secondary-link,
.secondary-button {
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

.error-banner,
.success-banner {
  box-sizing: border-box;
  margin-bottom: 16px;
  border-radius: 8px;
  padding: 12px 14px;
  font-weight: 700;
}

.error-banner {
  border: 1px solid #f4b4ad;
  background: #fff1f0;
  color: #9f1c12;
}

.success-banner {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #047857;
}

.import-card,
.commit-card,
.state-panel {
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
}

.import-card,
.commit-card {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
  padding: 22px;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.safe-note {
  margin: 0;
  color: #047857;
  font-weight: 800;
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

input[type='file'],
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
  color: #374151;
  font: inherit;
}

select {
  border-style: solid;
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
  .secondary-link,
  .secondary-button {
    justify-content: center;
    width: 100%;
  }
}
</style>

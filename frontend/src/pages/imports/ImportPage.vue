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
        <RouterLink class="back-link" to="/projects">返回项目列表</RouterLink>
        <p class="eyebrow">章枢 Next</p>
        <h1>导入作品</h1>
      </div>
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
  overflow-x: hidden;
  padding: var(--zs-space-8) var(--zs-space-5);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
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
  gap: var(--zs-space-6);
  margin-bottom: var(--zs-space-6);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

h1 {
  margin: 0;
  font-size: 1.8rem;
  line-height: 1.1;
  letter-spacing: 0;
}

.secondary-link,
.secondary-button {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-weight: 800;
  text-decoration: none;
}

.error-banner,
.success-banner {
  box-sizing: border-box;
  margin-bottom: var(--zs-space-4);
  border-radius: var(--zs-radius-md);
  padding: 12px 14px;
  font-weight: 700;
}

.error-banner {
  border: 1px solid var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.success-banner {
  border: 1px solid var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.import-card,
.commit-card,
.state-panel {
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
}

.import-card,
.commit-card {
  display: grid;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-5);
  padding: var(--zs-space-5);
  box-shadow: var(--zs-shadow-sm);
}

.safe-note {
  margin: 0;
  color: var(--zs-color-success);
  font-weight: 800;
}

.field-group,
.file-field {
  display: grid;
  gap: 8px;
}

.field-label,
.file-field span {
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.segmented-control {
  display: flex;
  flex-wrap: wrap;
  gap: var(--zs-space-2);
}

.segmented-control label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 10px 12px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
  font-weight: 800;
}

input[type='file'],
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

select {
  border-style: solid;
}

.actions-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
}

.file-note {
  margin: 0;
  color: var(--zs-color-text-muted);
  overflow-wrap: anywhere;
}

.state-panel {
  display: grid;
  place-items: center;
  min-height: 120px;
  margin-bottom: var(--zs-space-5);
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.preview-panel,
.report-panel {
  margin-top: var(--zs-space-5);
}

button {
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
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
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

@media (max-width: 720px) {
  .import-page {
    padding: var(--zs-space-6) var(--zs-space-4);
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

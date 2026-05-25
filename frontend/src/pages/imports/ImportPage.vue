<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import {
  commitProjectImport,
  confirmProjectPackageImport,
  previewProjectImport,
  previewProjectPackageImport,
} from '@/entities/import/api'
import type {
  ImportPreview,
  ImportReport,
  ProjectPackageImportConfirm,
  ProjectPackageImportPreview,
} from '@/entities/import/types'
import { listProjects } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import ImportPreviewPanel from '@/features/imports/ImportPreviewPanel.vue'
import ImportReportPanel from '@/features/imports/ImportReportPanel.vue'

const importTab = ref<'manuscript' | 'package'>('manuscript')

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

const packageFile = ref<File | null>(null)
const packagePreview = ref<ProjectPackageImportPreview | null>(null)
const packageReport = ref<ProjectPackageImportConfirm | null>(null)
const isPackagePreviewing = ref(false)
const isPackageConfirming = ref(false)

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

function handlePackageFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  packageFile.value = input.files?.[0] ?? null
  packagePreview.value = null
  packageReport.value = null
  errorMessage.value = ''
  successMessage.value = ''
}

async function handlePackagePreview() {
  if (!packageFile.value) {
    errorMessage.value = '请先选择备份文件。'
    return
  }

  isPackagePreviewing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  packageReport.value = null

  try {
    packagePreview.value = await previewProjectPackageImport(packageFile.value)
  } catch (error) {
    packagePreview.value = null
    errorMessage.value = getErrorMessage(error, '项目包预览失败，请检查文件格式')
  } finally {
    isPackagePreviewing.value = false
  }
}

async function handlePackageConfirm() {
  if (!packagePreview.value) {
    return
  }

  isPackageConfirming.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    packageReport.value = await confirmProjectPackageImport(packagePreview.value.preview_id)
    successMessage.value = '项目包导入成功'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '项目包导入失败')
  } finally {
    isPackageConfirming.value = false
  }
}

function handleTabChange(tab: 'manuscript' | 'package') {
  importTab.value = tab
  errorMessage.value = ''
  successMessage.value = ''
  preview.value = null
  report.value = null
  packagePreview.value = null
  packageReport.value = null
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

    <nav class="tab-bar" role="tablist" aria-label="导入类型">
      <button
        type="button"
        role="tab"
        :aria-selected="importTab === 'manuscript'"
        :class="{ active: importTab === 'manuscript' }"
        @click="handleTabChange('manuscript')"
      >
        导入正文
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="importTab === 'package'"
        :class="{ active: importTab === 'package' }"
        @click="handleTabChange('package')"
      >
        导入章枢项目包
      </button>
    </nav>

    <template v-if="importTab === 'manuscript'">
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
    </template>

    <template v-if="importTab === 'package'">
      <section class="import-card">
        <p class="panel-copy">
          适用于从章枢备份包迁移完整项目，包含人物、设定、伏笔、时间线、关系图、大纲等全部资料。导入后将创建为新项目。
        </p>

        <label class="file-field">
          <span>选择备份文件（.zip）</span>
          <input
            type="file"
            accept=".zip"
            @change="handlePackageFileChange"
          />
        </label>

        <div class="actions-row">
          <button
            class="primary-button"
            type="button"
            :disabled="isPackagePreviewing || !packageFile"
            @click="handlePackagePreview"
          >
            {{ isPackagePreviewing ? '正在预览…' : '预览项目包' }}
          </button>
        </div>
      </section>

      <section v-if="packagePreview" class="import-card package-preview">
        <header>
          <p class="eyebrow">项目包预览</p>
          <h2>{{ packagePreview.project_title }}</h2>
        </header>

        <div class="entity-grid">
          <div><dt>分卷</dt><dd>{{ packagePreview.entity_counts.volumes }}</dd></div>
          <div><dt>章节</dt><dd>{{ packagePreview.entity_counts.chapters }}</dd></div>
          <div><dt>人物</dt><dd>{{ packagePreview.entity_counts.characters }}</dd></div>
          <div><dt>设定</dt><dd>{{ packagePreview.entity_counts.settings }}</dd></div>
          <div><dt>伏笔</dt><dd>{{ packagePreview.entity_counts.clues }}</dd></div>
          <div><dt>大纲</dt><dd>{{ packagePreview.entity_counts.outlines }}</dd></div>
          <div><dt>时间线事件</dt><dd>{{ packagePreview.entity_counts.timeline_events }}</dd></div>
          <div><dt>关系图节点</dt><dd>{{ packagePreview.entity_counts.graph_nodes }}</dd></div>
        </div>

        <p v-if="packagePreview.has_cover" class="panel-copy">包含项目封面</p>

        <div v-if="packagePreview.warnings.length > 0" class="warning-list">
          <ul>
            <li v-for="warning in packagePreview.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <div class="actions-row">
          <button
            class="primary-button"
            type="button"
            :disabled="isPackageConfirming"
            @click="handlePackageConfirm"
          >
            {{ isPackageConfirming ? '正在导入…' : '确认导入为新项目' }}
          </button>
        </div>
      </section>

      <section v-if="packageReport" class="import-card package-report">
        <header>
          <p class="eyebrow">导入完成</p>
          <h2>{{ packageReport.project_title }}</h2>
        </header>

        <div class="entity-grid">
          <div><dt>分卷</dt><dd>{{ packageReport.entity_counts.volumes }}</dd></div>
          <div><dt>章节</dt><dd>{{ packageReport.entity_counts.chapters }}</dd></div>
          <div><dt>人物</dt><dd>{{ packageReport.entity_counts.characters }}</dd></div>
          <div><dt>设定</dt><dd>{{ packageReport.entity_counts.settings }}</dd></div>
          <div><dt>伏笔</dt><dd>{{ packageReport.entity_counts.clues }}</dd></div>
          <div><dt>大纲</dt><dd>{{ packageReport.entity_counts.outlines }}</dd></div>
        </div>

        <div v-if="packageReport.warnings.length > 0" class="warning-list">
          <h3>警告</h3>
          <ul>
            <li v-for="warning in packageReport.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <RouterLink class="primary-button open-link" :to="`/projects/${packageReport.project_id}`">
          打开导入的项目
        </RouterLink>
      </section>
    </template>
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
.report-panel,
.tab-bar {
  max-width: 980px;
  margin-right: auto;
  margin-left: auto;
}

.tab-bar {
  display: flex;
  gap: var(--zs-space-2);
  margin-bottom: var(--zs-space-5);
}

.tab-bar button {
  min-height: 40px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 0 18px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-weight: 800;
  cursor: pointer;
}

.tab-bar button.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.package-preview header,
.package-report header {
  margin-bottom: var(--zs-space-4);
}

.package-preview h2,
.package-report h2 {
  margin: 0;
  font-size: 1.25rem;
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--zs-space-3);
  margin: var(--zs-space-4) 0;
}

.entity-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface-soft);
}

.entity-grid dt {
  margin: 0 0 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.entity-grid dd {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.3rem;
  font-weight: 800;
}

.panel-copy {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.warning-list ul {
  margin: 8px 0 0;
  padding-left: 20px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  margin-top: var(--zs-space-4);
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

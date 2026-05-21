<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { downloadProjectBackup, restoreProjectBackup } from '@/entities/project/backupApi'
import type { RestoreReport } from '@/entities/project/backupTypes'
import { downloadManuscriptExport } from '@/entities/project/exportApi'
import type { ManuscriptExportFormat, ManuscriptExportScope } from '@/entities/project/exportTypes'
import { listVolumes } from '@/entities/volume/api'
import type { Volume } from '@/entities/volume/types'

const route = useRoute()

const backupFile = ref<File | null>(null)
const volumes = ref<Volume[]>([])
const chapters = ref<Chapter[]>([])
const exportScope = ref<ManuscriptExportScope>('project')
const exportFormat = ref<ManuscriptExportFormat>('txt')
const selectedVolumeId = ref('')
const selectedChapterId = ref('')
const isLoadingProjectData = ref(false)
const isExportingManuscript = ref(false)
const isExportingBackup = ref(false)
const isRestoring = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const restoreReport = ref<RestoreReport | null>(null)

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const sortedVolumes = computed(() =>
  [...volumes.value].sort((left, right) => left.order_index - right.order_index),
)

const sortedChapters = computed(() =>
  [...chapters.value].sort((left, right) => left.order_index - right.order_index),
)

const selectableChapters = computed(() => {
  if (exportScope.value === 'volume' && selectedVolumeId.value) {
    return sortedChapters.value.filter((chapter) => chapter.volume_id === selectedVolumeId.value)
  }
  return sortedChapters.value
})

onMounted(() => {
  void loadProjectData()
})

watch(projectId, () => {
  void loadProjectData()
})

watch(exportScope, () => {
  successMessage.value = ''
  errorMessage.value = ''
})

async function loadProjectData() {
  volumes.value = []
  chapters.value = []
  selectedVolumeId.value = ''
  selectedChapterId.value = ''

  if (!projectId.value) {
    return
  }

  isLoadingProjectData.value = true
  errorMessage.value = ''

  try {
    const [projectVolumes, projectChapters] = await Promise.all([
      listVolumes(projectId.value),
      listChapters(projectId.value),
    ])
    volumes.value = projectVolumes
    chapters.value = projectChapters
    selectedVolumeId.value = sortedVolumes.value[0]?.id ?? ''
    selectedChapterId.value = sortedChapters.value[0]?.id ?? ''
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载导出选项失败。')
  } finally {
    isLoadingProjectData.value = false
  }
}

function handleBackupFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  backupFile.value = input.files?.[0] ?? null
  restoreReport.value = null
  successMessage.value = ''
  errorMessage.value = ''
}

async function handleManuscriptExport() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  if (exportFormat.value === 'docx') {
    errorMessage.value = 'DOCX 导出暂未支持，请先选择 TXT 或 Markdown。'
    return
  }

  if (exportScope.value === 'volume' && !selectedVolumeId.value) {
    errorMessage.value = '请先选择要导出的分卷。'
    return
  }

  if (exportScope.value === 'chapter' && !selectedChapterId.value) {
    errorMessage.value = '请先选择要导出的章节。'
    return
  }

  isExportingManuscript.value = true
  successMessage.value = ''
  errorMessage.value = ''

  try {
    await downloadManuscriptExport(projectId.value, {
      scope: exportScope.value,
      volume_id: exportScope.value === 'volume' ? selectedVolumeId.value : null,
      chapter_id: exportScope.value === 'chapter' ? selectedChapterId.value : null,
      format: exportFormat.value,
    })
    successMessage.value = '导出成功'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '导出失败，请稍后重试')
  } finally {
    isExportingManuscript.value = false
  }
}

async function handleBackupExport() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isExportingBackup.value = true
  successMessage.value = ''
  errorMessage.value = ''

  try {
    await downloadProjectBackup(projectId.value)
    successMessage.value = '备份成功'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '导出项目备份失败')
  } finally {
    isExportingBackup.value = false
  }
}

async function handleRestore() {
  if (!backupFile.value) {
    errorMessage.value = '请先选择备份文件。'
    return
  }

  isRestoring.value = true
  successMessage.value = ''
  errorMessage.value = ''
  restoreReport.value = null

  try {
    restoreReport.value = await restoreProjectBackup(backupFile.value)
    successMessage.value = '恢复成功'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '恢复失败，请检查备份文件')
  } finally {
    isRestoring.value = false
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
  <main class="export-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="projectId ? `/projects/${projectId}` : '/projects'">
          {{ projectId ? '返回项目' : '返回项目列表' }}
        </RouterLink>
        <p class="eyebrow">导入导出</p>
        <h1>导出与备份</h1>
      </div>
      <RouterLink class="secondary-link" to="/projects">项目列表</RouterLink>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="successMessage" class="success-banner" role="status">
      {{ successMessage }}
    </section>

    <section class="page-layout">
      <article v-if="projectId" class="action-panel">
        <header>
          <p class="eyebrow">作品导出</p>
          <h2>导出作品</h2>
        </header>

        <div class="field-group">
          <span class="field-label">导出范围</span>
          <div class="segmented-control" role="radiogroup" aria-label="导出范围">
            <label>
              <input v-model="exportScope" type="radio" value="project" />
              <span>全书</span>
            </label>
            <label>
              <input v-model="exportScope" type="radio" value="volume" />
              <span>当前分卷</span>
            </label>
            <label>
              <input v-model="exportScope" type="radio" value="chapter" />
              <span>当前章节</span>
            </label>
          </div>
        </div>

        <label v-if="exportScope === 'volume'" class="field-group">
          <span class="field-label">当前分卷</span>
          <select v-model="selectedVolumeId" :disabled="isLoadingProjectData">
            <option v-for="volume in sortedVolumes" :key="volume.id" :value="volume.id">
              {{ volume.title }}
            </option>
          </select>
        </label>

        <label v-if="exportScope === 'chapter'" class="field-group">
          <span class="field-label">当前章节</span>
          <select v-model="selectedChapterId" :disabled="isLoadingProjectData">
            <option v-for="chapter in selectableChapters" :key="chapter.id" :value="chapter.id">
              {{ chapter.title }}
            </option>
          </select>
        </label>

        <div class="field-group">
          <span class="field-label">导出格式</span>
          <div class="segmented-control" role="radiogroup" aria-label="导出格式">
            <label>
              <input v-model="exportFormat" type="radio" value="txt" />
              <span>TXT</span>
            </label>
            <label>
              <input v-model="exportFormat" type="radio" value="md" />
              <span>Markdown</span>
            </label>
            <label>
              <input v-model="exportFormat" type="radio" value="docx" />
              <span>DOCX</span>
            </label>
          </div>
        </div>

        <p v-if="exportFormat === 'docx'" class="panel-note">
          DOCX 导出暂未支持，请先使用 TXT 或 Markdown。
        </p>

        <button
          class="primary-button"
          type="button"
          :disabled="isExportingManuscript || isLoadingProjectData"
          @click="handleManuscriptExport"
        >
          {{ isExportingManuscript ? '正在导出…' : '开始导出' }}
        </button>
      </article>

      <article v-if="projectId" class="action-panel">
        <header>
          <p class="eyebrow">项目备份</p>
          <h2>导出项目备份</h2>
        </header>
        <p class="panel-copy">
          生成用于章枢恢复的 zip 备份，包含项目、章节、素材、时间线、关系图和大纲数据。
        </p>
        <button class="primary-button" type="button" :disabled="isExportingBackup" @click="handleBackupExport">
          {{ isExportingBackup ? '正在导出…' : '导出项目备份' }}
        </button>
      </article>

      <article class="action-panel">
        <header>
          <p class="eyebrow">备份恢复</p>
          <h2>从备份恢复项目</h2>
        </header>
        <p class="panel-copy">
          恢复为新项目，不会覆盖原项目。恢复后可在项目列表中打开新的项目副本。
        </p>

        <label class="file-field">
          <span>备份文件</span>
          <input accept=".zip" type="file" @change="handleBackupFileChange" />
        </label>

        <div class="actions-row">
          <button
            class="primary-button"
            type="button"
            :disabled="isRestoring || !backupFile"
            @click="handleRestore"
          >
            {{ isRestoring ? '正在恢复…' : '恢复为新项目' }}
          </button>
          <p v-if="backupFile" class="file-note">已选择：{{ backupFile.name }}</p>
        </div>
      </article>
    </section>

    <section v-if="restoreReport" class="report-panel">
      <header class="report-header">
        <div>
          <p class="eyebrow">恢复报告</p>
          <h2>{{ restoreReport.project_title }}</h2>
        </div>
        <RouterLink class="open-link" :to="`/projects/${restoreReport.project_id}`">打开新项目</RouterLink>
      </header>

      <dl class="report-grid">
        <div>
          <dt>分卷</dt>
          <dd>{{ restoreReport.counts.volumes }}</dd>
        </div>
        <div>
          <dt>章节</dt>
          <dd>{{ restoreReport.counts.chapters }}</dd>
        </div>
        <div>
          <dt>素材</dt>
          <dd>{{ restoreReport.counts.materials }}</dd>
        </div>
      </dl>

      <div v-if="restoreReport.warnings.length > 0" class="warning-list">
        <h3>警告</h3>
        <ul>
          <li v-for="warning in restoreReport.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </div>

      <div v-if="restoreReport.errors.length > 0" class="error-list">
        <h3>错误</h3>
        <ul>
          <li v-for="error in restoreReport.errors" :key="error">{{ error }}</li>
        </ul>
      </div>
    </section>
  </main>
</template>

<style scoped>
.export-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 40px;
  background: #f6f8fb;
  color: #111827;
}

.page-header,
.page-layout,
.error-banner,
.success-banner,
.report-panel {
  max-width: 1120px;
  margin-right: auto;
  margin-left: auto;
}

.page-header,
.report-header,
.actions-row {
  display: flex;
  gap: 18px;
}

.page-header,
.report-header {
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
  align-items: stretch;
  margin-bottom: 18px;
}

.action-panel,
.report-panel {
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.action-panel {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 22px;
}

.report-panel {
  padding: 22px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
h3,
.panel-copy,
.panel-note,
.file-note {
  margin: 0;
}

h1 {
  font-size: 2rem;
  line-height: 1.1;
}

h2 {
  font-size: 1.25rem;
  line-height: 1.2;
}

h3 {
  font-size: 1rem;
}

.panel-copy,
.panel-note,
.file-note {
  color: #64748b;
  line-height: 1.6;
}

.panel-note {
  color: #b45309;
  font-weight: 800;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.secondary-link,
.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  box-sizing: border-box;
  border-radius: 6px;
  padding: 0 14px;
  font-weight: 800;
  text-decoration: none;
}

.secondary-link {
  border: 1px solid #cfd7e3;
  background: #ffffff;
  color: #374151;
}

.open-link {
  background: #2563eb;
  color: #ffffff;
}

.error-banner,
.success-banner {
  box-sizing: border-box;
  margin-bottom: 16px;
  border-radius: 8px;
  padding: 12px 14px;
  font-weight: 800;
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

select,
input[type='file'] {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
  color: #374151;
  font: inherit;
}

input[type='file'] {
  border-style: dashed;
}

.actions-row {
  align-items: center;
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

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.report-grid div {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}

dt {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

dd {
  margin: 0;
  color: #111827;
  font-size: 1.3rem;
  font-weight: 800;
}

.warning-list,
.error-list {
  margin-top: 14px;
}

ul {
  margin: 8px 0 0;
  padding-left: 20px;
  color: #4b5563;
  line-height: 1.6;
}

@media (max-width: 760px) {
  .export-page {
    padding: 24px 16px;
  }

  .page-header,
  .report-header,
  .actions-row {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button,
  .secondary-link,
  .open-link {
    width: 100%;
  }
}
</style>

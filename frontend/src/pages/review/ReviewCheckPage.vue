<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import {
  createProhibitedTerm,
  deleteProhibitedTerm,
  exportProhibitedTerms,
  importProhibitedTerms,
  listProhibitedTerms,
  listReviewResults,
  runReviewCheck,
  updateProhibitedTerm,
} from '@/entities/review/api'
import type { CheckResult, ProhibitedTerm, ReviewScope } from '@/entities/review/types'
import { listVolumes } from '@/entities/volume/api'
import type { Volume } from '@/entities/volume/types'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'

const route = useRoute()
const router = useRouter()

const terms = ref<ProhibitedTerm[]>([])
const volumes = ref<Volume[]>([])
const chapters = ref<Chapter[]>([])
const results = ref<CheckResult[]>([])
const scope = ref<ReviewScope>('chapter')
const selectedChapterId = ref('')
const selectedVolumeId = ref('')
const newTerm = ref('')
const newSeverity = ref('medium')
const newSuggestion = ref('')
const isLoading = ref(false)
const isChecking = ref(false)
const isSavingTerm = ref(false)
const isImportingTerms = ref(false)
const termImportInputRef = ref<HTMLInputElement | null>(null)
const errorMessage = ref('')
const successMessage = ref('')

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const workspaceStorageKey = computed(() => `zhangshu:workspace:${projectId.value}`)

const sortedVolumes = computed(() =>
  [...volumes.value].sort((left, right) => left.order_index - right.order_index),
)

const sortedChapters = computed(() =>
  [...chapters.value].sort((left, right) => left.order_index - right.order_index),
)

onMounted(() => {
  void loadPageData()
})

watch(projectId, () => {
  void loadPageData()
})

async function loadPageData() {
  if (!projectId.value) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [termList, volumeList, chapterList, resultResponse] = await Promise.all([
      listProhibitedTerms(),
      listVolumes(projectId.value),
      listChapters(projectId.value),
      listReviewResults(projectId.value),
    ])
    terms.value = termList
    volumes.value = volumeList
    chapters.value = chapterList
    results.value = resultResponse.results
    restoreCurrentSelection()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载检查数据失败。')
  } finally {
    isLoading.value = false
  }
}

function restoreCurrentSelection() {
  const state = safeReadJson<{ selectedChapterId?: unknown } | null>(workspaceStorageKey.value, null)
  const storedChapterId = typeof state?.selectedChapterId === 'string' ? state.selectedChapterId : ''
  selectedChapterId.value = chapters.value.some((chapter) => chapter.id === storedChapterId)
    ? storedChapterId
    : sortedChapters.value[0]?.id ?? ''
  const selectedChapter = chapters.value.find((chapter) => chapter.id === selectedChapterId.value)
  selectedVolumeId.value = selectedChapter?.volume_id || sortedVolumes.value[0]?.id || ''
}

async function handleCreateTerm() {
  const term = newTerm.value.trim()
  if (!term) {
    errorMessage.value = '请先输入违禁词或敏感词。'
    return
  }

  isSavingTerm.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await createProhibitedTerm({
      term,
      severity: newSeverity.value.trim() || 'medium',
      suggestion: newSuggestion.value.trim(),
      enabled: true,
    })
    newTerm.value = ''
    newSuggestion.value = ''
    successMessage.value = '词条已添加。'
    terms.value = await listProhibitedTerms()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '添加词条失败。')
  } finally {
    isSavingTerm.value = false
  }
}

async function handleToggleTerm(term: ProhibitedTerm) {
  try {
    const updated = await updateProhibitedTerm(term.id, { enabled: !term.enabled })
    terms.value = terms.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '更新词条失败。')
  }
}

async function handleDeleteTerm(term: ProhibitedTerm) {
  const confirmed = window.confirm(`确定删除“${term.term}”吗？`)
  if (!confirmed) {
    return
  }

  try {
    await deleteProhibitedTerm(term.id)
    terms.value = terms.value.filter((item) => item.id !== term.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除词条失败。')
  }
}

async function handleExportTerms() {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const blob = await exportProhibitedTerms()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `zhangshu_prohibited_terms_${formatDateForFilename(new Date())}.json`
    document.body.append(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '词库导出失败，请稍后重试。')
  }
}

function openImportTermsPicker() {
  termImportInputRef.value?.click()
}

async function handleImportTerms(event: Event) {
  const input = event.target
  if (!(input instanceof HTMLInputElement) || !input.files?.[0]) {
    return
  }

  const file = input.files[0]
  input.value = ''
  isImportingTerms.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const report = await importProhibitedTerms(file)
    terms.value = await listProhibitedTerms()
    successMessage.value = `已导入 ${report.imported_count} 条，更新 ${report.updated_count} 条，跳过 ${report.skipped_count} 条。`
    if (report.errors.length > 0) {
      errorMessage.value = report.errors.slice(0, 3).join(' ')
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '词库导入失败，请检查文件格式。')
  } finally {
    isImportingTerms.value = false
  }
}

async function handleCheck() {
  if (scope.value === 'chapter' && !selectedChapterId.value) {
    errorMessage.value = '请先选择章节。'
    return
  }
  if (scope.value === 'volume' && !selectedVolumeId.value) {
    errorMessage.value = '请先选择分卷。'
    return
  }

  isChecking.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await runReviewCheck(projectId.value, {
      scope: scope.value,
      chapter_id: scope.value === 'chapter' ? selectedChapterId.value : null,
      volume_id: scope.value === 'volume' ? selectedVolumeId.value : null,
    })
    results.value = response.results
    successMessage.value = `检查完成，共发现 ${response.total} 条结果。`
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '检查失败，请稍后重试。')
  } finally {
    isChecking.value = false
  }
}

async function openChapter(result: CheckResult) {
  const currentState = safeReadJson<Record<string, unknown> | null>(workspaceStorageKey.value, null)
  safeWriteJson(workspaceStorageKey.value, {
    ...(currentState ?? {}),
    selectedChapterId: result.chapter_id,
  })
  await router.push(`/projects/${projectId.value}`)
}

function getSeverityLabel(value: string): string {
  if (value === 'high') {
    return '高'
  }
  if (value === 'low') {
    return '低'
  }
  return '中'
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function formatDateForFilename(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`
}
</script>

<template>
  <main class="review-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" to="/projects">返回项目列表</RouterLink>
        <p class="eyebrow">检查</p>
        <h1>违禁词 / 敏感词检查</h1>
      </div>
      <RouterLink class="secondary-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>
    <section v-if="successMessage" class="success-banner" role="status">
      {{ successMessage }}
    </section>

    <section class="page-layout">
      <article class="panel">
        <header>
          <p class="eyebrow">检查</p>
          <h2>检查</h2>
        </header>
        <p class="panel-note">检查功能只提示，不会自动修改正文</p>

        <div class="field-group">
          <span class="field-label">检查范围</span>
          <div class="segmented-control" role="radiogroup" aria-label="检查范围">
            <label>
              <input v-model="scope" type="radio" value="chapter" />
              <span>当前章节</span>
            </label>
            <label>
              <input v-model="scope" type="radio" value="volume" />
              <span>当前分卷</span>
            </label>
            <label>
              <input v-model="scope" type="radio" value="project" />
              <span>全书</span>
            </label>
          </div>
        </div>

        <label v-if="scope === 'chapter'" class="field-group">
          <span class="field-label">当前章节</span>
          <select v-model="selectedChapterId" :disabled="isLoading">
            <option v-for="chapter in sortedChapters" :key="chapter.id" :value="chapter.id">
              {{ chapter.title }}
            </option>
          </select>
        </label>

        <label v-if="scope === 'volume'" class="field-group">
          <span class="field-label">当前分卷</span>
          <select v-model="selectedVolumeId" :disabled="isLoading">
            <option v-for="volume in sortedVolumes" :key="volume.id" :value="volume.id">
              {{ volume.title }}
            </option>
          </select>
        </label>

        <button class="primary-button" type="button" :disabled="isChecking || isLoading" @click="handleCheck">
          {{ isChecking ? '正在检查…' : '开始检查' }}
        </button>
      </article>

      <article class="panel">
        <header class="term-panel-header">
          <div>
            <p class="eyebrow">词库</p>
            <h2>违禁词 / 敏感词</h2>
          </div>
          <div class="term-toolbar">
            <button class="secondary-button" type="button" :disabled="isImportingTerms" @click="openImportTermsPicker">
              {{ isImportingTerms ? '导入中…' : '导入词库' }}
            </button>
            <button class="secondary-button" type="button" @click="handleExportTerms">导出词库</button>
            <input
              ref="termImportInputRef"
              class="visually-hidden"
              type="file"
              accept="application/json,.json"
              @change="handleImportTerms"
            />
          </div>
        </header>

        <form class="term-form" @submit.prevent="handleCreateTerm">
          <label class="field-group">
            <span class="field-label">匹配词</span>
            <input v-model="newTerm" type="text" />
          </label>
          <label class="field-group">
            <span class="field-label">严重程度</span>
            <select v-model="newSeverity">
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
          </label>
          <label class="field-group">
            <span class="field-label">建议</span>
            <input v-model="newSuggestion" type="text" />
          </label>
          <button class="primary-button" type="submit" :disabled="isSavingTerm">
            {{ isSavingTerm ? '正在添加…' : '添加词条' }}
          </button>
        </form>

        <div class="term-list">
          <article v-for="term in terms" :key="term.id" class="term-item">
            <div>
              <strong>{{ term.term }}</strong>
              <span>{{ getSeverityLabel(term.severity) }}</span>
            </div>
            <p>{{ term.suggestion || '暂无建议' }}</p>
            <div class="term-actions">
              <button class="secondary-button" type="button" @click="handleToggleTerm(term)">
                {{ term.enabled ? '停用' : '启用' }}
              </button>
              <button class="danger-button" type="button" @click="handleDeleteTerm(term)">删除</button>
            </div>
          </article>
          <p v-if="terms.length === 0" class="empty-state">暂无词条</p>
        </div>
      </article>
    </section>

    <section class="result-panel">
      <header class="result-title">
        <p class="eyebrow">检查结果</p>
        <h2>检查结果</h2>
      </header>

      <article v-for="result in results" :key="result.id" class="result-card">
        <header class="result-header">
          <div>
            <p class="volume-title">{{ result.volume_title || '未分卷章节' }}</p>
            <h3>{{ result.chapter_title || '章节' }}</h3>
          </div>
          <span class="severity-pill">{{ getSeverityLabel(result.severity) }}</span>
        </header>

        <dl class="result-grid">
          <div>
            <dt>匹配词</dt>
            <dd>{{ result.matched_text }}</dd>
          </div>
          <div>
            <dt>严重程度</dt>
            <dd>{{ getSeverityLabel(result.severity) }}</dd>
          </div>
          <div>
            <dt>位置</dt>
            <dd>{{ result.position_start }}-{{ result.position_end }}</dd>
          </div>
        </dl>

        <p class="suggestion"><strong>建议：</strong>{{ result.suggestion || '请结合上下文人工判断。' }}</p>
        <footer class="result-footer">
          <button class="secondary-button" type="button" @click="openChapter(result)">打开章节</button>
        </footer>
      </article>

      <p v-if="results.length === 0" class="empty-state">暂无检查结果</p>
    </section>
  </main>
</template>

<style scoped>
.review-page {
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
.result-panel {
  max-width: 1120px;
  margin-right: auto;
  margin-left: auto;
}

.page-header,
.page-layout,
.result-header,
.term-actions,
.result-footer,
.term-panel-header,
.term-toolbar {
  display: flex;
  gap: 16px;
}

.page-header {
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
}

.term-panel-header {
  align-items: flex-start;
  justify-content: space-between;
}

.term-toolbar {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.page-layout {
  align-items: flex-start;
  margin-bottom: 18px;
}

.panel,
.result-panel,
.result-card {
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.panel {
  flex: 1 1 0;
  display: grid;
  gap: 16px;
  padding: 22px;
}

.result-panel {
  display: grid;
  gap: 14px;
  padding: 22px;
}

.result-card {
  display: grid;
  gap: 14px;
  padding: 18px;
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
.panel-note,
.volume-title,
.suggestion,
.empty-state {
  margin: 0;
}

h1 {
  font-size: 2rem;
  line-height: 1.1;
}

h2 {
  font-size: 1.25rem;
}

h3 {
  font-size: 1.05rem;
}

.panel-note,
.volume-title,
.suggestion {
  color: #64748b;
  line-height: 1.6;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 14px;
  background: #ffffff;
  color: #374151;
  font-weight: 800;
  text-decoration: none;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
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
.term-form {
  display: grid;
  gap: 8px;
}

.field-label {
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

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
  color: #111827;
  font: inherit;
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

.secondary-button {
  border-color: #cfd7e3;
  background: #ffffff;
  color: #2563eb;
}

.danger-button {
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}

.term-list {
  display: grid;
  gap: 10px;
}

.term-item {
  display: grid;
  gap: 8px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}

.term-item div:first-child {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.term-item p {
  margin: 0;
  color: #64748b;
}

.result-header,
.result-footer {
  align-items: center;
  justify-content: space-between;
}

.severity-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.78rem;
  font-weight: 800;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 0;
}

.result-grid div {
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
  font-weight: 800;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 120px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  font-weight: 800;
}

@media (max-width: 820px) {
  .review-page {
    padding: 24px 16px;
  }

  .page-header,
  .page-layout,
  .result-header,
  .result-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button,
  .secondary-button,
  .danger-button,
  .secondary-link {
    width: 100%;
  }
}
</style>

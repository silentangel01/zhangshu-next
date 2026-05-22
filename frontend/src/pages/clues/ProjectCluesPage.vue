<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { createClue, deleteClue, getClue, listProjectClues, updateClue } from '@/entities/clue/api'
import type { Clue, ClueImportance, ClueStatus, ClueVisibility } from '@/entities/clue/types'
import { clueImportanceLabels, clueStatusLabels, clueVisibilityLabels } from '@/entities/clue/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const chapters = ref<Chapter[]>([])
const clues = ref<Clue[]>([])
const selectedClue = ref<Clue | null>(null)
const isCreating = ref(true)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const filters = reactive({
  keyword: '',
  status: '',
  visibility: '',
  importance: '',
})

const form = reactive({
  title: '',
  description: '',
  setup_chapter_id: '',
  payoff_chapter_id: '',
  status: 'planned' as ClueStatus,
  visibility: 'hidden' as ClueVisibility,
  importance: 'normal' as ClueImportance,
  payoff_plan: '',
  actual_payoff: '',
  note: '',
})

const statuses: ClueStatus[] = ['planned', 'planted', 'developing', 'resolved', 'abandoned']
const visibilities: ClueVisibility[] = ['hidden', 'hinted', 'revealed']
const importances: ClueImportance[] = ['low', 'normal', 'high', 'critical']

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const chapterTitleMap = computed(() => {
  return chapters.value.reduce<Record<string, string>>((acc, chapter) => {
    acc[chapter.id] = chapter.title
    return acc
  }, {})
})

onMounted(() => {
  void loadWorkspace()
})

watch(projectId, () => {
  selectedClue.value = null
  resetForm()
  void loadWorkspace()
})

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [projectDetail, projectChapters, projectClues] = await Promise.all([
      getProject(projectId.value),
      listChapters(projectId.value),
      listProjectClues(projectId.value, buildFilters()),
    ])
    project.value = projectDetail
    chapters.value = projectChapters
    clues.value = projectClues
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载伏笔库失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshClues() {
  if (!projectId.value) {
    return
  }
  clues.value = await listProjectClues(projectId.value, buildFilters())
  if (selectedClue.value) {
    selectedClue.value = clues.value.find((clue) => clue.id === selectedClue.value?.id) ?? null
  }
}

function buildFilters() {
  return {
    keyword: filters.keyword.trim() || undefined,
    status: (filters.status || undefined) as ClueStatus | undefined,
    visibility: (filters.visibility || undefined) as ClueVisibility | undefined,
    importance: (filters.importance || undefined) as ClueImportance | undefined,
  }
}

async function handleApplyFilters() {
  await saveSafe(async () => {
    await refreshClues()
  }, '筛选伏笔失败。')
}

async function handleSelectClue(clue: Clue) {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedClue.value = await getClue(clue.id)
    isCreating.value = false
    applyClueToForm(selectedClue.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载伏笔详情失败。')
  }
}

function handleNewClue() {
  selectedClue.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
}

async function handleSaveClue() {
  if (!projectId.value) {
    return
  }

  await saveSafe(async () => {
    const payload = {
      title: form.title,
      description: form.description,
      setup_chapter_id: form.setup_chapter_id || null,
      payoff_chapter_id: form.payoff_chapter_id || null,
      status: form.status,
      visibility: form.visibility,
      importance: form.importance,
      payoff_plan: form.payoff_plan,
      actual_payoff: form.actual_payoff,
      note: form.note,
    }

    const saved = isCreating.value
      ? await createClue(projectId.value, payload)
      : await updateClue(selectedClue.value!.id, payload)

    selectedClue.value = saved
    isCreating.value = false
    applyClueToForm(saved)
    await refreshClues()
    successMessage.value = '伏笔已保存。'
  }, '保存伏笔失败。')
}

async function handleDeleteClue() {
  if (!selectedClue.value) {
    return
  }

  const confirmed = window.confirm(`确认删除伏笔“${selectedClue.value.title}”吗？`)
  if (!confirmed) {
    return
  }

  await saveSafe(async () => {
    await deleteClue(selectedClue.value!.id)
    selectedClue.value = null
    isCreating.value = true
    resetForm()
    await refreshClues()
    successMessage.value = '伏笔已删除。'
  }, '删除伏笔失败。')
}

async function handleOpenGraphNode() {
  if (!selectedClue.value || !projectId.value) {
    return
  }
  await saveSafe(async () => {
    const node = await ensureMaterialGraphNode({
      projectId: projectId.value,
      boundType: 'clue',
      boundId: selectedClue.value!.id,
      nodeType: 'clue',
      title: selectedClue.value!.title,
      summary: selectedClue.value!.description || selectedClue.value!.payoff_plan,
    })
    await router.push(graphFocusRoute(projectId.value, node.id))
  }, '打开关系图节点失败。')
}

async function saveSafe(action: () => Promise<void>, fallback: string) {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await action()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, fallback)
  } finally {
    isSaving.value = false
  }
}

function applyClueToForm(clue: Clue) {
  form.title = clue.title
  form.description = clue.description
  form.setup_chapter_id = clue.setup_chapter_id ?? ''
  form.payoff_chapter_id = clue.payoff_chapter_id ?? ''
  form.status = clue.status
  form.visibility = clue.visibility
  form.importance = clue.importance
  form.payoff_plan = clue.payoff_plan
  form.actual_payoff = clue.actual_payoff
  form.note = clue.note
}

function resetForm() {
  form.title = ''
  form.description = ''
  form.setup_chapter_id = ''
  form.payoff_chapter_id = ''
  form.status = 'planned'
  form.visibility = 'hidden'
  form.importance = 'normal'
  form.payoff_plan = ''
  form.actual_payoff = ''
  form.note = ''
}

function getChapterTitle(chapterId: string | null) {
  if (!chapterId) {
    return '未绑定'
  }
  return chapterTitleMap.value[chapterId] ?? '未知章节'
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="clues-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">剧情线索管理</p>
        <h1>伏笔库</h1>
        <p class="project-title">{{ project?.title || '正在加载项目…' }}</p>
        <p class="page-note">伏笔库用于追踪线索的埋设、推进、回收和废弃状态，避免长篇写作中遗漏重要剧情线索。</p>
      </div>
      <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewClue">
        新建伏笔
      </button>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载伏笔库…</section>

    <section v-else class="clues-layout">
      <aside class="list-panel">
        <div class="filters">
          <input v-model="filters.keyword" type="search" placeholder="搜索标题、描述、回收计划、备注" />
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option v-for="status in statuses" :key="status" :value="status">{{ clueStatusLabels[status] }}</option>
          </select>
          <select v-model="filters.visibility">
            <option value="">全部可见程度</option>
            <option v-for="visibility in visibilities" :key="visibility" :value="visibility">
              {{ clueVisibilityLabels[visibility] }}
            </option>
          </select>
          <select v-model="filters.importance">
            <option value="">全部重要程度</option>
            <option v-for="importance in importances" :key="importance" :value="importance">
              {{ clueImportanceLabels[importance] }}
            </option>
          </select>
          <button class="secondary-button" type="button" :disabled="isSaving" @click="handleApplyFilters">
            筛选
          </button>
        </div>

        <p v-if="clues.length === 0" class="empty-state">暂无伏笔，请先新建伏笔。</p>

        <ul v-else class="clue-list">
          <li v-for="clue in clues" :key="clue.id">
            <button
              class="clue-card"
              type="button"
              :class="{ active: selectedClue?.id === clue.id }"
              @click="handleSelectClue(clue)"
            >
              <span class="name">{{ clue.title }}</span>
              <span class="meta">
                {{ clueStatusLabels[clue.status] }} ·
                {{ clueVisibilityLabels[clue.visibility] }} ·
                {{ clueImportanceLabels[clue.importance] }}
              </span>
              <span class="chapter-line">埋设：{{ getChapterTitle(clue.setup_chapter_id) }}</span>
              <span class="chapter-line">回收：{{ getChapterTitle(clue.payoff_chapter_id) }}</span>
              <span class="summary">{{ clue.description || '暂无描述' }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <form class="editor-panel" @submit.prevent="handleSaveClue">
        <header class="editor-header">
          <div>
            <p class="eyebrow">{{ isCreating ? '新建伏笔' : '伏笔详情' }}</p>
            <h2>{{ form.title || '未命名伏笔' }}</h2>
          </div>
          <span v-if="selectedClue" class="version">v{{ selectedClue.version }}</span>
        </header>

        <div class="form-grid">
          <label>
            <span>标题</span>
            <input v-model.trim="form.title" type="text" required />
          </label>
          <label>
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="status in statuses" :key="status" :value="status">{{ clueStatusLabels[status] }}</option>
            </select>
          </label>
          <label>
            <span>可见程度</span>
            <select v-model="form.visibility">
              <option v-for="visibility in visibilities" :key="visibility" :value="visibility">
                {{ clueVisibilityLabels[visibility] }}
              </option>
            </select>
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="form.importance">
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ clueImportanceLabels[importance] }}
              </option>
            </select>
          </label>
          <label>
            <span>埋设章节</span>
            <select v-model="form.setup_chapter_id">
              <option value="">未绑定</option>
              <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
            </select>
          </label>
          <label>
            <span>回收章节</span>
            <select v-model="form.payoff_chapter_id">
              <option value="">未绑定</option>
              <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
            </select>
          </label>
        </div>

        <label>
          <span>描述</span>
          <textarea v-model="form.description" rows="4" />
        </label>

        <div class="text-grid">
          <label><span>回收计划</span><textarea v-model="form.payoff_plan" rows="5" /></label>
          <label><span>实际回收</span><textarea v-model="form.actual_payoff" rows="5" /></label>
          <label><span>备注</span><textarea v-model="form.note" rows="5" /></label>
        </div>

        <footer class="editor-actions">
          <button
            class="secondary-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedClue"
            @click="handleOpenGraphNode"
          >
            在关系图中查看
          </button>
          <button
            class="danger-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedClue"
            @click="handleDeleteClue"
          >
            删除伏笔
          </button>
          <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
            {{ isSaving ? '正在保存…' : '保存伏笔' }}
          </button>
        </footer>
      </form>
      <MaterialLinkPanel
        v-if="selectedClue"
        :project-id="projectId"
        source-type="clue"
        :source-id="selectedClue.id"
        :source-title="selectedClue.title"
        :allowed-target-types="['outline', 'character', 'setting', 'timeline_event', 'graph_node']"
        compact
      />
    </section>
  </main>
</template>

<style scoped>
.clues-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: #f6f8fb;
  color: #111827;
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.clues-layout {
  max-width: 1280px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.project-title,
.page-note {
  margin: 0;
  color: #64748b;
  font-weight: 800;
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 0.78rem;
}

.page-note {
  max-width: 760px;
  margin-top: 10px;
  line-height: 1.7;
  font-weight: 700;
}

h1,
h2 {
  margin: 0;
  line-height: 1.15;
}

h1 {
  margin-bottom: 8px;
  font-size: 2rem;
}

h2 {
  font-size: 1.35rem;
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

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  text-align: center;
}

.clues-layout {
  display: grid;
  grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.list-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.filters {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 12px;
  color: #111827;
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.clue-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.clue-card {
  display: grid;
  gap: 6px;
  width: 100%;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.clue-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.name {
  font-size: 1rem;
  font-weight: 800;
}

.meta,
.chapter-line,
.summary {
  color: #64748b;
  font-size: 0.86rem;
  line-height: 1.5;
}

.summary {
  color: #374151;
}

.editor-panel {
  display: grid;
  gap: 16px;
}

.editor-header,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-grid,
.text-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 7px;
  color: #4b5563;
  font-weight: 800;
}

.version {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.78rem;
  font-weight: 800;
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
  color: #374151;
}

.danger-button {
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}

@media (max-width: 860px) {
  .clues-page {
    padding: 24px 16px;
  }

  .page-header,
  .clues-layout {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>

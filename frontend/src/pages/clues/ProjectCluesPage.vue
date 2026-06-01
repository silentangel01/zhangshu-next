<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { createClue, deleteClue, getClue, listProjectClues, updateClue } from '@/entities/clue/api'
import type { Clue, ClueImportance, ClueStatus, ClueVisibility } from '@/entities/clue/types'
import { clueImportanceLabels, clueStatusLabels, clueVisibilityLabels } from '@/entities/clue/types'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'
import { useDebouncedAutosave } from '@/shared/composables/useDebouncedAutosave'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { listVolumes } from '@/entities/volume/api'
import type { Volume } from '@/entities/volume/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'

type ClueGroupMode = 'setup' | 'payoff'

interface ClueTreeVolumeNode {
  kind: 'volume'
  key: string
  title: string
  clueCount: number
}

interface ClueTreeChapterNode {
  kind: 'chapter'
  key: string
  title: string
  clueCount: number
}

interface ClueTreeClueNode {
  kind: 'clue'
  key: string
  clue: Clue
}

type ClueTreeNode = ClueTreeVolumeNode | ClueTreeChapterNode | ClueTreeClueNode

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const volumes = ref<Volume[]>([])
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

let isApplyingForm = false
let lastSavedPayload = ''

function buildCluePayload() {
  return {
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
}

const autosave = useDebouncedAutosave({
  delayMs: 3000,
  canSave: () =>
    !isCreating.value &&
    selectedClue.value !== null &&
    !!projectId.value &&
    form.title.trim() !== '' &&
    !isSaving.value,
  hasChanges: () => JSON.stringify(buildCluePayload()) !== lastSavedPayload,
  save: async () => {
    const saved = await updateClue(selectedClue.value!.id, buildCluePayload())
    selectedClue.value = saved
    isApplyingForm = true
    applyClueToForm(saved)
    isApplyingForm = false
    await refreshClues()
    cloudSyncManager.notifyDirty(projectId.value)
    lastSavedPayload = JSON.stringify(buildCluePayload())
  },
})

const autosaveStatusText = computed(() => {
  switch (autosave.status.value) {
    case 'dirty': return '有未保存修改'
    case 'saving': return '正在自动保存…'
    case 'saved': return '已自动保存'
    case 'error': return '自动保存失败，请手动保存'
    default: return ''
  }
})

watch(
  () => ({ ...form }),
  () => {
    if (isApplyingForm) return
    autosave.schedule()
  },
  { deep: true },
)

const statuses: ClueStatus[] = ['planned', 'planted', 'developing', 'resolved', 'abandoned']
const visibilities: ClueVisibility[] = ['hidden', 'hinted', 'revealed']
const importances: ClueImportance[] = ['low', 'normal', 'high', 'critical']

// --- Filter panel state ---
const isFilterPanelOpen = ref(false)

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.status) count++
  if (filters.visibility) count++
  if (filters.importance) count++
  return count
})

// --- Group mode ---
const clueGroupMode = ref<ClueGroupMode>('setup')

// --- Tree expand state ---
const expandedTreeKeys = ref<Set<string>>(new Set())

function isTreeExpanded(key: string): boolean {
  return expandedTreeKeys.value.has(key)
}

function toggleTreeNode(key: string): void {
  const next = new Set(expandedTreeKeys.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedTreeKeys.value = next
}

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

const volumeById = computed(() => {
  const map = new Map<string, Volume>()
  for (const v of volumes.value) map.set(v.id, v)
  return map
})

const chapterById = computed(() => {
  const map = new Map<string, Chapter>()
  for (const c of chapters.value) map.set(c.id, c)
  return map
})

const chaptersByVolumeId = computed(() => {
  const map = new Map<string, Chapter[]>()
  for (const c of chapters.value) {
    const vid = c.volume_id ?? '__unvolumed__'
    const list = map.get(vid)
    if (list) {
      list.push(c)
    } else {
      map.set(vid, [c])
    }
  }
  return map
})

const hasActiveSearchOrFilter = computed(() => {
  return !!(filters.keyword.trim() || filters.status || filters.visibility || filters.importance)
})

const clueTree = computed<ClueTreeNode[]>(() => {
  const chapterMap = chapterById.value
  const volMap = volumeById.value
  const groupKey = clueGroupMode.value === 'setup' ? 'setup_chapter_id' : 'payoff_chapter_id'

  // Bucket clues into groups
  interface BucketEntry {
    volume: Volume | null // null = unvolumed
    chapter: Chapter | null // null = unbound
    clues: Clue[]
    volumeKey: string
    chapterKey: string
    volumeTitle: string
    chapterTitle: string
  }

  const bucketMap = new Map<string, BucketEntry>()

  function getOrCreateBucket(
    chapter: Chapter | null,
    volume: Volume | null,
    bucketKey: string,
    volumeKey: string,
    volumeTitle: string,
    chapterTitle: string,
  ): BucketEntry {
    let entry = bucketMap.get(bucketKey)
    if (!entry) {
      entry = { volume, chapter, clues: [], volumeKey, chapterKey: bucketKey, volumeTitle, chapterTitle }
      bucketMap.set(bucketKey, entry)
    }
    return entry
  }

  for (const clue of clues.value) {
    const chapterId = clue[groupKey]
    if (!chapterId) {
      // Unbound
      const vKey = '__unbound__'
      const cKey = '__unbound_chapter__'
      const modeLabel = clueGroupMode.value === 'setup' ? '未绑定埋设章节' : '未绑定回收章节'
      getOrCreateBucket(null, null, cKey, vKey, modeLabel, modeLabel).clues.push(clue)
      continue
    }

    const chapter = chapterMap.get(chapterId)
    if (!chapter) {
      // Chapter not found (deleted or not in project)
      const vKey = '__unknown__'
      const cKey = `__unknown_${chapterId}__`
      getOrCreateBucket(null, null, cKey, vKey, '未知章节', '未知章节').clues.push(clue)
      continue
    }

    const volume = chapter.volume_id ? volMap.get(chapter.volume_id) ?? null : null
    const vKey = chapter.volume_id ?? '__unvolumed__'
    const vTitle = volume?.title ?? '未分卷'
    const cKey = chapter.id
    getOrCreateBucket(chapter, volume, cKey, vKey, vTitle, chapter.title).clues.push(clue)
  }

  // Organize into volume groups
  interface VolumeGroup {
    volumeKey: string
    volumeTitle: string
    volumeOrder: number
    isSpecial: boolean
    chapters: {
      chapterKey: string
      chapterTitle: string
      chapterOrder: number
      isSpecial: boolean
      clues: Clue[]
    }[]
    totalClues: number
  }

  const volumeGroupMap = new Map<string, VolumeGroup>()

  for (const entry of bucketMap.values()) {
    let vg = volumeGroupMap.get(entry.volumeKey)
    if (!vg) {
      const volOrder = entry.volume ? entry.volume.order_index : 999999
      const isSpecial = entry.volumeKey === '__unbound__' || entry.volumeKey === '__unknown__' || entry.volumeKey === '__unvolumed__'
      vg = {
        volumeKey: entry.volumeKey,
        volumeTitle: entry.volumeTitle,
        volumeOrder: isSpecial ? 999999 : volOrder,
        isSpecial,
        chapters: [],
        totalClues: 0,
      }
      volumeGroupMap.set(entry.volumeKey, vg)
    }

    const chapterOrder = entry.chapter ? entry.chapter.order_index : 999999
    const isChapterSpecial = entry.chapterKey.startsWith('__')
    vg.chapters.push({
      chapterKey: entry.chapterKey,
      chapterTitle: entry.chapterTitle,
      chapterOrder: isChapterSpecial ? 999999 : chapterOrder,
      isSpecial: isChapterSpecial,
      clues: entry.clues,
    })
    vg.totalClues += entry.clues.length
  }

  // Sort volumes
  const sortedVolumes = [...volumeGroupMap.values()].sort((a, b) => {
    if (a.isSpecial !== b.isSpecial) return a.isSpecial ? 1 : -1
    if (a.volumeOrder !== b.volumeOrder) return a.volumeOrder - b.volumeOrder
    return a.volumeTitle.localeCompare(b.volumeTitle)
  })

  // Sort chapters within each volume and build flat tree
  const nodes: ClueTreeNode[] = []

  for (const vg of sortedVolumes) {
    vg.chapters.sort((a, b) => {
      if (a.isSpecial !== b.isSpecial) return a.isSpecial ? 1 : -1
      if (a.chapterOrder !== b.chapterOrder) return a.chapterOrder - b.chapterOrder
      return a.chapterTitle.localeCompare(b.chapterTitle)
    })

    nodes.push({
      kind: 'volume',
      key: vg.volumeKey,
      title: vg.volumeTitle,
      clueCount: vg.totalClues,
    })

    if (!isTreeExpanded(vg.volumeKey)) continue

    for (const ch of vg.chapters) {
      nodes.push({
        kind: 'chapter',
        key: ch.chapterKey,
        title: ch.chapterTitle,
        clueCount: ch.clues.length,
      })

      if (!isTreeExpanded(ch.chapterKey)) continue

      for (const clue of ch.clues) {
        nodes.push({ kind: 'clue', key: clue.id, clue })
      }
    }
  }

  return nodes
})

// Auto-expand volumes when tree first loads
function autoExpandTree(): void {
  if (expandedTreeKeys.value.size > 0) return
  const keys = new Set<string>()
  const chapterMap = chapterById.value
  const volMap = volumeById.value
  const groupKey = clueGroupMode.value === 'setup' ? 'setup_chapter_id' : 'payoff_chapter_id'

  for (const clue of clues.value) {
    const chapterId = clue[groupKey]
    if (!chapterId) {
      keys.add('__unbound__')
      keys.add('__unbound_chapter__')
      continue
    }
    const chapter = chapterMap.get(chapterId)
    if (!chapter) {
      keys.add('__unknown__')
      keys.add(`__unknown_${chapterId}__`)
      continue
    }
    const vKey = chapter.volume_id ?? '__unvolumed__'
    keys.add(vKey)
    keys.add(chapter.id)
  }

  expandedTreeKeys.value = keys
}

onMounted(() => {
  void loadWorkspace()
})

watch(projectId, () => {
  autosave.cancel()
  selectedClue.value = null
  lastSavedPayload = ''
  resetForm()
  void loadWorkspace()
})

watch(clueGroupMode, () => {
  expandedTreeKeys.value = new Set()
  autoExpandTree()
})

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [projectDetail, projectVolumes, projectChapters, projectClues] = await Promise.all([
      getProject(projectId.value),
      listVolumes(projectId.value),
      listChapters(projectId.value),
      listProjectClues(projectId.value, buildFilters()),
    ])
    project.value = projectDetail
    volumes.value = projectVolumes
    chapters.value = projectChapters
    clues.value = projectClues
    autoExpandTree()
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

function handleClearStructuredFilters() {
  filters.status = ''
  filters.visibility = ''
  filters.importance = ''
  void handleApplyFilters()
}

async function handleSelectClue(clue: Clue) {
  if (selectedClue.value && !isCreating.value) {
    const flushed = await autosave.flush()
    if (!flushed) return
  }

  autosave.cancel()
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedClue.value = await getClue(clue.id)
    isCreating.value = false
    isApplyingForm = true
    applyClueToForm(selectedClue.value)
    isApplyingForm = false
    lastSavedPayload = JSON.stringify(buildCluePayload())
    autosave.markSaved()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载伏笔详情失败。')
  }
}

function handleNewClue() {
  autosave.cancel()
  selectedClue.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
  lastSavedPayload = ''
}

async function handleSaveClue() {
  if (!projectId.value) {
    return
  }

  autosave.cancel()

  await saveSafe(async () => {
    const payload = buildCluePayload()

    const saved = isCreating.value
      ? await createClue(projectId.value, payload)
      : await updateClue(selectedClue.value!.id, payload)

    selectedClue.value = saved
    isCreating.value = false
    isApplyingForm = true
    applyClueToForm(saved)
    isApplyingForm = false
    await refreshClues()
    successMessage.value = '伏笔已保存。'
    cloudSyncManager.notifyDirty(projectId.value)
    lastSavedPayload = JSON.stringify(buildCluePayload())
    autosave.markSaved()
  }, '保存伏笔失败。')
}

async function handleDeleteClue() {
  if (!selectedClue.value) {
    return
  }

  if (!isCreating.value) {
    const flushed = await autosave.flush()
    if (!flushed) return
  }

  const confirmed = window.confirm(`确认删除伏笔”${selectedClue.value.title}”吗？`)
  if (!confirmed) {
    return
  }

  autosave.cancel()

  await saveSafe(async () => {
    await deleteClue(selectedClue.value!.id)
    selectedClue.value = null
    isCreating.value = true
    resetForm()
    lastSavedPayload = ''
    await refreshClues()
    successMessage.value = '伏笔已删除。'
    cloudSyncManager.notifyDirty(projectId.value)
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
    cloudSyncManager.notifyDirty(projectId.value)
    await router.push(
      graphFocusRoute(projectId.value, node.id, {
        returnTo: 'clues',
        returnId: selectedClue.value!.id,
        returnLabel: selectedClue.value!.title,
      }),
    )
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
  <main class="clues-page material-page">
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

    <!-- Toolbar: search + filter + group mode -->
    <div class="clues-toolbar">
      <div class="search-group">
        <input
          v-model="filters.keyword"
          type="search"
          placeholder="搜索标题、描述、回收计划、备注"
          @keyup.enter="handleApplyFilters"
        />
        <button class="secondary-button" type="button" :disabled="isSaving" @click="handleApplyFilters">
          搜索
        </button>
      </div>
      <div class="filter-menu">
        <button
          class="secondary-button"
          type="button"
          :class="{ active: isFilterPanelOpen || activeFilterCount > 0 }"
          @click="isFilterPanelOpen = !isFilterPanelOpen"
        >
          筛选{{ activeFilterCount > 0 ? `（${activeFilterCount}）` : '' }}
        </button>
        <div v-if="isFilterPanelOpen" class="filter-panel">
          <label>
            <span>伏笔状态</span>
            <select v-model="filters.status">
              <option value="">全部状态</option>
              <option v-for="status in statuses" :key="status" :value="status">{{ clueStatusLabels[status] }}</option>
            </select>
          </label>
          <label>
            <span>可见程度</span>
            <select v-model="filters.visibility">
              <option value="">全部可见程度</option>
              <option v-for="visibility in visibilities" :key="visibility" :value="visibility">
                {{ clueVisibilityLabels[visibility] }}
              </option>
            </select>
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="filters.importance">
              <option value="">全部重要程度</option>
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ clueImportanceLabels[importance] }}
              </option>
            </select>
          </label>
          <div class="filter-actions">
            <button class="secondary-button" type="button" @click="handleClearStructuredFilters">
              清空筛选
            </button>
            <button
              class="primary-button"
              type="button"
              @click="isFilterPanelOpen = false; handleApplyFilters()"
            >
              应用筛选
            </button>
          </div>
        </div>
      </div>
      <div class="tree-mode-control">
        <button
          class="mode-button"
          type="button"
          :class="{ active: clueGroupMode === 'setup' }"
          @click="clueGroupMode = 'setup'"
        >
          按埋设章节
        </button>
        <button
          class="mode-button"
          type="button"
          :class="{ active: clueGroupMode === 'payoff' }"
          @click="clueGroupMode = 'payoff'"
        >
          按回收章节
        </button>
      </div>
    </div>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载伏笔库…</section>

    <section v-else class="clues-layout material-layout">
      <aside class="list-panel material-list-panel">
        <p v-if="clues.length === 0 && !hasActiveSearchOrFilter" class="empty-state">暂无伏笔，请先新建伏笔。</p>
        <p v-else-if="clues.length === 0 && hasActiveSearchOrFilter" class="empty-state">没有符合条件的伏笔。</p>

        <ul v-else class="clue-tree">
          <template v-for="node in clueTree" :key="node.key">
            <li v-if="node.kind === 'volume'" class="tree-volume">
              <button
                class="tree-node-button"
                type="button"
                @click="toggleTreeNode(node.key)"
              >
                <span class="tree-caret">{{ isTreeExpanded(node.key) ? '▾' : '▸' }}</span>
                <span class="tree-node-title">{{ node.title }}</span>
                <span class="tree-count">{{ node.clueCount }}</span>
              </button>
            </li>
            <li v-else-if="node.kind === 'chapter'" class="tree-chapter">
              <button
                class="tree-node-button"
                type="button"
                @click="toggleTreeNode(node.key)"
              >
                <span class="tree-caret">{{ isTreeExpanded(node.key) ? '▾' : '▸' }}</span>
                <span class="tree-node-title">{{ node.title }}</span>
                <span class="tree-count">{{ node.clueCount }}</span>
              </button>
            </li>
            <li v-else-if="node.kind === 'clue'" class="tree-clue">
              <button
                class="clue-card"
                type="button"
                :class="{ active: selectedClue?.id === node.clue.id }"
                @click="handleSelectClue(node.clue)"
              >
                <span class="name">{{ node.clue.title }}</span>
                <span class="meta">
                  {{ clueStatusLabels[node.clue.status] }} ·
                  {{ clueVisibilityLabels[node.clue.visibility] }} ·
                  {{ clueImportanceLabels[node.clue.importance] }}
                </span>
                <span class="chapter-line">埋设：{{ getChapterTitle(node.clue.setup_chapter_id) }}</span>
                <span class="chapter-line">回收：{{ getChapterTitle(node.clue.payoff_chapter_id) }}</span>
                <span class="summary">{{ node.clue.description || '暂无描述' }}</span>
              </button>
            </li>
          </template>
        </ul>
      </aside>

      <form class="editor-panel material-editor-panel" @submit.prevent="handleSaveClue">
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
          <span v-if="!isCreating && autosaveStatusText" class="autosave-status">{{ autosaveStatusText }}</span>
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
      <aside class="material-related-panel">
        <MaterialLinkPanel
          v-if="selectedClue"
          :project-id="projectId"
          source-type="clue"
          :source-id="selectedClue.id"
          :source-title="selectedClue.title"
          :allowed-target-types="['outline', 'character', 'setting', 'timeline_event', 'graph_node']"
          compact
        />
        <article v-else class="empty-state related-empty">暂无关联资料</article>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.clues-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.clues-toolbar,
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
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.project-title,
.page-note {
  margin: 0;
  color: var(--zs-color-text-muted);
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
  border: 1px solid var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.success-banner {
  border: 1px solid var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  text-align: center;
}

.clues-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) minmax(280px, 320px);
  gap: 18px;
  align-items: start;
}

.list-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 20px;
  background: var(--zs-color-surface);
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.filters {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

/* --- Toolbar: search + filter + group mode --- */
.clues-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  max-width: 1480px;
  margin-right: auto;
  margin-left: auto;
  margin-bottom: 16px;
}

.search-group {
  display: flex;
  flex: 1 1 280px;
  gap: 8px;
  min-width: 0;
}

.search-group input {
  flex: 1;
  min-width: 0;
}

.filter-menu {
  position: relative;
}

.filter-menu .secondary-button.active {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.filter-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 10;
  display: grid;
  gap: 10px;
  min-width: 240px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  background: var(--zs-color-surface);
  box-shadow: 0 8px 24px rgb(20 24 31 / 12%);
}

.filter-actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.tree-mode-control {
  display: flex;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  overflow: hidden;
}

.mode-button {
  border: none;
  border-radius: 0;
  padding: 0 12px;
  min-height: 36px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
}

.mode-button + .mode-button {
  border-left: 1px solid var(--zs-color-border);
}

.mode-button.active {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

/* --- Clue tree --- */
.clue-tree {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tree-volume,
.tree-chapter,
.tree-clue {
  min-width: 0;
}

.tree-chapter {
  padding-left: 16px;
}

.tree-clue {
  padding-left: 32px;
}

.tree-node-button {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  border: none;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.88rem;
  font-weight: 800;
  text-align: left;
  cursor: pointer;
}

.tree-node-button:hover {
  background: var(--zs-color-surface-soft);
}

.tree-caret {
  flex: 0 0 auto;
  width: 14px;
  color: var(--zs-color-text-faint);
  font-size: 0.78rem;
}

.tree-node-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-count {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 1px 8px;
  background: var(--zs-color-border);
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

.clue-tree .clue-card {
  margin-bottom: 4px;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 10px 12px;
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.clue-card {
  display: grid;
  gap: 6px;
  width: 100%;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.clue-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.name {
  font-size: 1rem;
  font-weight: 800;
}

.meta,
.chapter-line,
.summary {
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
  line-height: 1.5;
}

.summary {
  color: var(--zs-color-text);
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
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.version {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
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
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
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

  .clues-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .tree-mode-control {
    align-self: flex-start;
  }
}

.material-page {
  overflow-x: hidden;
  padding: var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.material-page .page-header,
.material-page .clues-toolbar,
.material-page .error-banner,
.material-page .success-banner,
.material-page .state-message,
.material-layout {
  max-width: 1480px;
}

.material-page .page-header {
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-4);
}

.material-page .back-link {
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
}

.material-page .eyebrow,
.material-page .project-title,
.material-page .page-note,
.material-page .meta,
.material-page .chapter-line {
  color: var(--zs-color-text-muted);
}

.material-page h1 {
  font-size: 1.6rem;
}

.material-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) minmax(280px, 320px);
  gap: var(--zs-space-4);
  align-items: start;
}

.material-list-panel,
.material-editor-panel,
.material-related-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.material-page input,
.material-page select,
.material-page textarea {
  border-color: var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .clue-card {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .clue-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.material-page .empty-state,
.material-page .state-message {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
}

.material-page .error-banner {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.material-page .success-banner {
  border-color: var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.material-page .primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.material-page .secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.material-page .version {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.material-page .tree-node-button:hover {
  background: var(--zs-color-primary-soft);
}

.material-page .tree-count {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.material-page .tree-node-title {
  color: var(--zs-color-text);
}

.material-page .mode-button {
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border-color: var(--zs-color-border);
}

.material-page .mode-button + .mode-button {
  border-left-color: var(--zs-color-border);
}

.material-page .mode-button.active {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.material-page .filter-panel {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md, 0 8px 24px rgb(20 24 31 / 12%));
}

@media (max-width: 1366px) {
  .material-page {
    padding: var(--zs-space-4);
  }

  .material-layout {
    grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  }

  .material-related-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .material-layout {
    grid-template-columns: 1fr;
  }
}

.autosave-status {
  margin-right: auto;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}
</style>

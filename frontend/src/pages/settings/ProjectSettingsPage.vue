<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createSetting,
  deleteSetting,
  getSetting,
  listProjectSettings,
  updateSetting,
} from '@/entities/setting/api'
import type {
  SettingCanonStatus,
  SettingImportance,
  SettingItem,
  SettingItemType,
  SettingNodeKind,
} from '@/entities/setting/types'
import {
  settingCanonStatusLabels,
  settingImportanceLabels,
  settingItemTypeLabels,
} from '@/entities/setting/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'

interface SettingTreeItem {
  setting: SettingItem
  level: number
}

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const settings = ref<SettingItem[]>([])
const allSettings = ref<SettingItem[]>([])
const selectedSetting = ref<SettingItem | null>(null)
const isCreating = ref(true)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const filters = reactive({
  keyword: '',
  item_type: '',
  canon_status: '',
  importance: '',
})

const form = reactive({
  parent_id: '',
  title: '',
  item_type: 'location' as SettingItemType,
  canon_status: 'draft' as SettingCanonStatus,
  importance: 'normal' as SettingImportance,
  tags: '',
  summary: '',
  detail: '',
  order_index: 0,
  node_kind: 'page' as SettingNodeKind,
  folder_default_item_type: 'custom' as SettingItemType | null,
})

const itemTypes: SettingItemType[] = [
  'world',
  'location',
  'organization',
  'power_system',
  'history',
  'technology',
  'rule',
  'race',
  'object',
  'character',
  'custom',
]
const canonStatuses: SettingCanonStatus[] = ['draft', 'confirmed', 'deprecated', 'conflicted']
const importances: SettingImportance[] = ['low', 'normal', 'high', 'critical']

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const treeItems = computed<SettingTreeItem[]>(() => buildTree(settings.value))

const parentOptions = computed(() =>
  allSettings.value.filter(
    (setting) =>
      setting.id !== selectedSetting.value?.id && setting.node_kind === 'folder',
  ),
)

const folders = computed(() =>
  allSettings.value.filter((s) => s.node_kind === 'folder'),
)

const selectedFolder = computed(() => {
  if (!selectedSetting.value) return null
  if (selectedSetting.value.node_kind === 'folder') return selectedSetting.value
  if (selectedSetting.value.parent_id) {
    return allSettings.value.find((s) => s.id === selectedSetting.value?.parent_id) ?? null
  }
  return null
})

const inheritedTypeLabel = computed(() => {
  if (!selectedSetting.value || selectedSetting.value.node_kind !== 'page') return ''
  const parentFolder = allSettings.value.find(
    (s) => s.id === selectedSetting.value?.parent_id,
  )
  if (parentFolder?.folder_default_item_type) {
    return settingItemTypeLabels[parentFolder.folder_default_item_type] ?? parentFolder.folder_default_item_type
  }
  return settingItemTypeLabels[selectedSetting.value.item_type] ?? selectedSetting.value.item_type
})

const selectedFolderId = ref<string | null>(null)

// --- Filter panel state ---
const isFilterPanelOpen = ref(false)

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.item_type) count++
  if (filters.canon_status) count++
  if (filters.importance) count++
  return count
})

// --- Drag-and-drop state ---
const draggedSettingId = ref<string | null>(null)
const dragOverFolderId = ref<string | null>(null)
const isMovingSetting = ref(false)
const pendingMove = ref<{ page: SettingItem; targetFolder: SettingItem } | null>(null)

// --- Drag helpers ---
function getSettingById(id: string): SettingItem | undefined {
  return allSettings.value.find((s) => s.id === id)
}

// --- Filter handlers ---
function handleClearStructuredFilters() {
  filters.item_type = ''
  filters.canon_status = ''
  filters.importance = ''
  isFilterPanelOpen.value = false
  void handleApplyFilters()
}

// --- Drag handlers ---
function handleSettingDragStart(event: DragEvent, setting: SettingItem) {
  if (setting.node_kind !== 'page' || isSaving.value || isMovingSetting.value) {
    event.preventDefault()
    return
  }
  draggedSettingId.value = setting.id
  if (event.dataTransfer) {
    event.dataTransfer.setData('text/plain', setting.id)
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleSettingDragEnd() {
  draggedSettingId.value = null
  dragOverFolderId.value = null
}

function handleFolderDragOver(event: DragEvent, folder: SettingItem) {
  if (folder.node_kind !== 'folder' || !draggedSettingId.value) return
  event.preventDefault()
  dragOverFolderId.value = folder.id
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleFolderDragLeave(folder: SettingItem) {
  if (dragOverFolderId.value === folder.id) {
    dragOverFolderId.value = null
  }
}

async function handleSettingDrop(_event: DragEvent, targetFolder: SettingItem) {
  const pageId = draggedSettingId.value
  draggedSettingId.value = null
  dragOverFolderId.value = null

  if (!pageId) return
  if (targetFolder.node_kind !== 'folder') return

  const page = getSettingById(pageId)
  if (!page || page.node_kind !== 'page') return
  if (page.parent_id === targetFolder.id) return // same folder, no-op

  // Check type difference
  const targetType = targetFolder.folder_default_item_type
  if (targetType && targetType !== page.item_type) {
    pendingMove.value = { page, targetFolder }
    return
  }

  // Types match or target has no default type — move directly
  await moveSettingToFolder(page, targetFolder, 'inherit')
}

// --- Move confirmation handlers ---
async function confirmMoveWithTypeChange() {
  if (!pendingMove.value) return
  const { page, targetFolder } = pendingMove.value
  pendingMove.value = null
  await moveSettingToFolder(page, targetFolder, 'inherit')
}

async function confirmMoveKeepType() {
  if (!pendingMove.value) return
  const { page, targetFolder } = pendingMove.value
  pendingMove.value = null
  await moveSettingToFolder(page, targetFolder, 'keep')
}

function cancelPendingMove() {
  pendingMove.value = null
}

async function moveSettingToFolder(
  page: SettingItem,
  targetFolder: SettingItem,
  mode: 'inherit' | 'keep',
) {
  isMovingSetting.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const payload =
      mode === 'inherit'
        ? { parent_id: targetFolder.id }
        : { parent_id: targetFolder.id, item_type: page.item_type }

    const updated = await updateSetting(page.id, payload)
    await refreshSettings()
    selectedSetting.value =
      allSettings.value.find((s) => s.id === updated.id) ?? null
    if (selectedSetting.value) {
      applySettingToForm(selectedSetting.value)
    }
    selectedFolderId.value = targetFolder.id
    successMessage.value = '设定已移动。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '移动设定失败。')
  } finally {
    isMovingSetting.value = false
  }
}

onMounted(() => {
  void loadWorkspace()
})

watch(projectId, () => {
  selectedSetting.value = null
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
    const [projectDetail, projectSettings, unfilteredSettings] = await Promise.all([
      getProject(projectId.value),
      listProjectSettings(projectId.value, buildFilters()),
      listProjectSettings(projectId.value),
    ])
    project.value = projectDetail
    settings.value = projectSettings
    allSettings.value = unfilteredSettings
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载设定集失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshSettings() {
  if (!projectId.value) {
    return
  }

  const [filteredSettings, unfilteredSettings] = await Promise.all([
    listProjectSettings(projectId.value, buildFilters()),
    listProjectSettings(projectId.value),
  ])
  settings.value = filteredSettings
  allSettings.value = unfilteredSettings

  if (selectedSetting.value) {
    selectedSetting.value =
      allSettings.value.find((setting) => setting.id === selectedSetting.value?.id) ?? null
  }
}

function buildFilters() {
  return {
    keyword: filters.keyword.trim() || undefined,
    item_type: (filters.item_type || undefined) as SettingItemType | undefined,
    canon_status: (filters.canon_status || undefined) as SettingCanonStatus | undefined,
    importance: (filters.importance || undefined) as SettingImportance | undefined,
  }
}

async function handleApplyFilters() {
  await saveSafe(async () => {
    await refreshSettings()
  }, '筛选设定失败。')
}

async function handleSelectSetting(setting: SettingItem) {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedSetting.value = await getSetting(setting.id)
    isCreating.value = false
    applySettingToForm(selectedSetting.value)

    // Track selected folder for creating new items under it
    if (setting.node_kind === 'folder') {
      selectedFolderId.value = setting.id
    } else if (setting.parent_id) {
      selectedFolderId.value = setting.parent_id
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载设定详情失败。')
  }
}

function handleNewSetting() {
  selectedSetting.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
  form.node_kind = 'page'
  if (selectedFolderId.value) {
    form.parent_id = selectedFolderId.value
  }
}

function handleNewFolder() {
  selectedSetting.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
  form.node_kind = 'folder'
  form.title = ''
  if (selectedFolderId.value) {
    form.parent_id = selectedFolderId.value
  }
}

async function handleSaveSetting() {
  if (!projectId.value) {
    return
  }

  await saveSafe(async () => {
    const isFolder = form.node_kind === 'folder'
    const payload = {
      parent_id: form.parent_id || null,
      title: form.title,
      item_type: isFolder ? undefined : form.item_type,
      canon_status: isFolder ? undefined : form.canon_status,
      importance: isFolder ? undefined : form.importance,
      tags: isFolder ? undefined : form.tags,
      summary: isFolder ? undefined : form.summary,
      detail: isFolder ? undefined : form.detail,
      order_index: Number(form.order_index) || 0,
      node_kind: form.node_kind,
      folder_default_item_type: isFolder ? form.folder_default_item_type : undefined,
    }

    const saved = isCreating.value
      ? await createSetting(projectId.value, payload)
      : await updateSetting(selectedSetting.value!.id, payload)

    selectedSetting.value = saved
    isCreating.value = false
    applySettingToForm(saved)
    await refreshSettings()
    successMessage.value = '设定已保存。'
  }, '保存设定失败。')
}

async function handleDeleteSetting() {
  if (!selectedSetting.value) {
    return
  }

  const confirmed = window.confirm(`确认删除设定“${selectedSetting.value.title}”吗？`)
  if (!confirmed) {
    return
  }

  await saveSafe(async () => {
    await deleteSetting(selectedSetting.value!.id)
    selectedSetting.value = null
    isCreating.value = true
    resetForm()
    await refreshSettings()
    successMessage.value = '设定已删除。'
  }, '删除设定失败。')
}

async function handleOpenGraphNode() {
  if (!selectedSetting.value || !projectId.value) {
    return
  }
  await saveSafe(async () => {
    const node = await ensureMaterialGraphNode({
      projectId: projectId.value,
      boundType: 'setting',
      boundId: selectedSetting.value!.id,
      nodeType: 'setting',
      title: selectedSetting.value!.title,
      summary: selectedSetting.value!.summary || selectedSetting.value!.detail,
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

function buildTree(items: SettingItem[]): SettingTreeItem[] {
  const allItems = allSettings.value
  const matchIds = new Set(items.map((item) => item.id))

  // When filtering, include ancestor folders of matched items to keep tree intact
  const visibleIds = new Set<string>(matchIds)
  if (items.length < allItems.length) {
    const byId = new Map(allItems.map((s) => [s.id, s]))
    for (const item of items) {
      let currentId = item.parent_id
      while (currentId && !visibleIds.has(currentId)) {
        visibleIds.add(currentId)
        const ancestor = byId.get(currentId)
        currentId = ancestor?.parent_id ?? null
      }
    }
  }

  const visibleItems = allItems.filter((s) => visibleIds.has(s.id))
  const childrenByParent = new Map<string, SettingItem[]>()
  const ids = new Set(visibleItems.map((item) => item.id))
  const roots: SettingItem[] = []

  for (const item of visibleItems) {
    if (!item.parent_id || !ids.has(item.parent_id)) {
      roots.push(item)
      continue
    }

    const children = childrenByParent.get(item.parent_id) ?? []
    children.push(item)
    childrenByParent.set(item.parent_id, children)
  }

  const sortItems = (left: SettingItem, right: SettingItem) => {
    // Folders first, then pages
    if (left.node_kind !== right.node_kind) {
      return left.node_kind === 'folder' ? -1 : 1
    }
    return left.order_index - right.order_index || left.title.localeCompare(right.title, 'zh-Hans-CN')
  }

  roots.sort(sortItems)
  for (const children of childrenByParent.values()) {
    children.sort(sortItems)
  }

  const result: SettingTreeItem[] = []
  const visit = (item: SettingItem, level: number) => {
    result.push({ setting: item, level })
    for (const child of childrenByParent.get(item.id) ?? []) {
      visit(child, level + 1)
    }
  }

  for (const root of roots) {
    visit(root, 0)
  }

  return result
}

function applySettingToForm(setting: SettingItem) {
  form.parent_id = setting.parent_id ?? ''
  form.title = setting.title
  form.item_type = setting.item_type
  form.canon_status = setting.canon_status
  form.importance = setting.importance
  form.tags = setting.tags
  form.summary = setting.summary
  form.detail = setting.detail
  form.order_index = setting.order_index
  form.node_kind = setting.node_kind
  form.folder_default_item_type = setting.folder_default_item_type ?? 'custom'
}

function resetForm() {
  form.parent_id = ''
  form.title = ''
  form.item_type = 'location'
  form.canon_status = 'draft'
  form.importance = 'normal'
  form.tags = ''
  form.summary = ''
  form.detail = ''
  form.order_index = 0
  form.node_kind = 'page'
  form.folder_default_item_type = 'custom'
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="settings-page material-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">本书内部设定</p>
        <h1>设定集</h1>
        <p class="project-title">{{ project?.title || '正在加载项目…' }}</p>
        <p class="boundary-note">
          设定集用于保存本书自设，如世界观、地点、组织、历史、规则和力量体系。外部素材和参考资料后续放入知识库，不在这里混用。
        </p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="isSaving" @click="handleNewFolder">
          新建目录
        </button>
        <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewSetting">
          新建设定
        </button>
      </div>
    </header>

    <!-- Toolbar: search + filter button -->
    <div class="settings-toolbar">
      <div class="search-group">
        <input
          v-model="filters.keyword"
          type="search"
          placeholder="搜索标题、简介、详细设定或标签"
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
            <span>类型</span>
            <select v-model="filters.item_type">
              <option value="">全部类型</option>
              <option v-for="itemType in itemTypes" :key="itemType" :value="itemType">
                {{ settingItemTypeLabels[itemType] }}
              </option>
            </select>
          </label>
          <label>
            <span>确认状态</span>
            <select v-model="filters.canon_status">
              <option value="">全部确认状态</option>
              <option v-for="status in canonStatuses" :key="status" :value="status">
                {{ settingCanonStatusLabels[status] }}
              </option>
            </select>
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="filters.importance">
              <option value="">全部重要程度</option>
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ settingImportanceLabels[importance] }}
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
    </div>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载设定集…</section>

    <section v-else class="settings-layout material-layout">
      <aside class="list-panel material-list-panel">
        <p class="boundary-card">这里保存的是本书内部设定。外部资料、灵感素材和参考内容后续将放入知识库模块。</p>

        <p v-if="settings.length === 0" class="empty-state">暂无设定，请先新建设定。</p>

        <ul v-else class="setting-list">
          <li v-for="item in treeItems" :key="item.setting.id">
            <button
              class="setting-card"
              type="button"
              :class="{
                active: selectedSetting?.id === item.setting.id,
                'is-folder': item.setting.node_kind === 'folder',
                dragging: draggedSettingId === item.setting.id,
                'drop-target': dragOverFolderId === item.setting.id,
              }"
              :style="{ paddingLeft: `${12 + item.level * 18}px` }"
              :draggable="item.setting.node_kind === 'page' && !isSaving && !isMovingSetting"
              @click="handleSelectSetting(item.setting)"
              @dragstart="handleSettingDragStart($event, item.setting)"
              @dragend="handleSettingDragEnd"
              @dragover="handleFolderDragOver($event, item.setting)"
              @dragleave="handleFolderDragLeave(item.setting)"
              @drop="handleSettingDrop($event, item.setting)"
            >
              <span class="title">
                <span v-if="item.setting.node_kind === 'folder'" class="node-icon">&#x1F4C1;</span>
                <span v-else class="node-icon">&#x1F4C4;</span>
                {{ item.setting.title }}
              </span>
              <span v-if="item.setting.node_kind === 'page'" class="meta">
                {{ settingItemTypeLabels[item.setting.item_type] }} ·
                {{ settingCanonStatusLabels[item.setting.canon_status] }} ·
                {{ settingImportanceLabels[item.setting.importance] }}
              </span>
              <span v-else-if="item.setting.folder_default_item_type" class="meta">
                目录 · 默认类型：{{ settingItemTypeLabels[item.setting.folder_default_item_type] }}
              </span>
              <span v-else class="meta">目录</span>
              <span v-if="item.setting.node_kind === 'page' && item.setting.tags" class="tags">{{ item.setting.tags }}</span>
              <span v-if="item.setting.node_kind === 'page'" class="summary">{{ item.setting.summary || '暂无简介' }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <form class="editor-panel material-editor-panel" @submit.prevent="handleSaveSetting">
        <header class="editor-header">
          <div>
            <p class="eyebrow">{{ isCreating ? '新建设定' : '设定条目' }}</p>
            <h2>{{ form.title || '未命名设定' }}</h2>
          </div>
          <span v-if="selectedSetting" class="version">v{{ selectedSetting.version }}</span>
        </header>

        <div class="form-grid">
          <label>
            <span>标题</span>
            <input v-model.trim="form.title" type="text" required />
          </label>
          <template v-if="form.node_kind === 'folder'">
            <label>
              <span>默认设定类型</span>
              <select v-model="form.folder_default_item_type">
                <option v-for="itemType in itemTypes" :key="itemType" :value="itemType">
                  {{ settingItemTypeLabels[itemType] }}
                </option>
              </select>
            </label>
          </template>
          <template v-else>
            <label v-if="!isCreating && selectedFolder">
              <span>类型（继承自目录）</span>
              <input :value="inheritedTypeLabel" type="text" disabled />
            </label>
            <label v-else-if="isCreating">
              <span>类型（由目录继承）</span>
              <input :value="inheritedTypeLabel || '自动继承'" type="text" disabled />
            </label>
            <label>
              <span>确认状态</span>
              <select v-model="form.canon_status">
                <option v-for="status in canonStatuses" :key="status" :value="status">
                  {{ settingCanonStatusLabels[status] }}
                </option>
              </select>
            </label>
            <label>
              <span>重要程度</span>
              <select v-model="form.importance">
                <option v-for="importance in importances" :key="importance" :value="importance">
                  {{ settingImportanceLabels[importance] }}
                </option>
              </select>
            </label>
          </template>
          <label>
            <span>所属目录</span>
            <select v-model="form.parent_id">
              <option value="">无（根级）</option>
              <option v-for="folder in parentOptions" :key="folder.id" :value="folder.id">
                {{ folder.title }}
              </option>
            </select>
          </label>
          <label>
            <span>排序序号</span>
            <input v-model.number="form.order_index" type="number" min="0" />
          </label>
        </div>

        <template v-if="form.node_kind !== 'folder'">
          <label>
            <span>标签</span>
            <input v-model.trim="form.tags" type="text" placeholder="例如：边城,主线地点" />
          </label>

          <label>
            <span>简介</span>
            <textarea v-model="form.summary" rows="3" />
          </label>

          <label>
            <span>详细设定</span>
            <textarea v-model="form.detail" rows="10" />
          </label>
        </template>

        <footer class="editor-actions">
          <button
            v-if="form.node_kind === 'page'"
            class="secondary-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedSetting"
            @click="handleOpenGraphNode"
          >
            在关系图中查看
          </button>
          <button
            v-if="!selectedSetting?.is_system"
            class="danger-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedSetting"
            @click="handleDeleteSetting"
          >
            删除{{ form.node_kind === 'folder' ? '目录' : '设定' }}
          </button>
          <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
            {{ isSaving ? '正在保存…' : '保存' }}
          </button>
        </footer>
      </form>
      <aside class="material-related-panel">
        <MaterialLinkPanel
          v-if="selectedSetting && selectedSetting.node_kind === 'page'"
          :project-id="projectId"
          source-type="setting"
          :source-id="selectedSetting.id"
          :source-title="selectedSetting.title"
        />
        <article v-else class="empty-state related-empty">
          {{ selectedSetting?.node_kind === 'folder' ? '目录无关联资料' : '暂无关联资料' }}
        </article>
      </aside>
    </section>

    <!-- Move confirmation panel -->
    <div v-if="pendingMove" class="move-confirm-overlay" @click.self="cancelPendingMove">
      <div class="move-confirm-panel">
        <h3>确认移动设定</h3>
        <p>
          「{{ pendingMove.page.title }}」当前类型为「{{ settingItemTypeLabels[pendingMove.page.item_type] }}」，
          目标目录「{{ pendingMove.targetFolder.title }}」默认类型为「{{ settingItemTypeLabels[pendingMove.targetFolder.folder_default_item_type!] }}」。
        </p>
        <div class="move-confirm-actions">
          <button class="primary-button" type="button" @click="confirmMoveWithTypeChange">
            自动更改类型
          </button>
          <button class="secondary-button" type="button" @click="confirmMoveKeepType">
            仅移动
          </button>
          <button class="danger-button" type="button" @click="cancelPendingMove">
            取消
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.settings-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.settings-layout {
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
.boundary-note {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 0.78rem;
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

.boundary-note {
  max-width: 780px;
  margin-top: 12px;
  font-weight: 700;
  line-height: 1.7;
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

.settings-layout {
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

.boundary-card {
  margin: 0 0 14px;
  border: 1px solid var(--zs-color-info-soft);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-info);
  font-weight: 800;
  line-height: 1.7;
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

.setting-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.setting-card {
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

.setting-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.title {
  font-size: 1rem;
  font-weight: 800;
}

.node-icon {
  margin-right: 4px;
  font-size: 0.85rem;
}

.setting-card.is-folder {
  font-weight: 800;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* --- Toolbar: search + filter --- */
.settings-toolbar {
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

/* --- Drag-and-drop --- */
.setting-card.dragging {
  opacity: 0.4;
}

.setting-card.drop-target {
  border-color: var(--zs-color-primary);
  border-style: dashed;
  background: var(--zs-color-primary-soft);
}

/* --- Move confirmation --- */
.move-confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: rgb(0 0 0 / 30%);
}

.move-confirm-panel {
  display: grid;
  gap: 14px;
  max-width: 420px;
  border: 1px solid var(--zs-color-border);
  border-radius: 10px;
  padding: 24px;
  background: var(--zs-color-surface);
  box-shadow: 0 16px 48px rgb(20 24 31 / 16%);
}

.move-confirm-panel h3 {
  margin: 0;
  font-size: 1.05rem;
}

.move-confirm-panel p {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.7;
}

.move-confirm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.meta,
.tags,
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

.form-grid {
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
  .settings-page {
    padding: 24px 16px;
  }

  .page-header,
  .settings-layout {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}

.material-page {
  overflow-x: hidden;
  padding: var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.material-page .page-header,
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
.material-page .boundary-note,
.material-page .meta,
.material-page .tags {
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

.material-page .setting-card {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .setting-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.material-page .boundary-card {
  border-color: var(--zs-color-info);
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
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
</style>

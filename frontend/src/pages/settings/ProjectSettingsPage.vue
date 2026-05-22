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
  allSettings.value.filter((setting) => setting.id !== selectedSetting.value?.id),
)

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
}

async function handleSaveSetting() {
  if (!projectId.value) {
    return
  }

  await saveSafe(async () => {
    const payload = {
      parent_id: form.parent_id || null,
      title: form.title,
      item_type: form.item_type,
      canon_status: form.canon_status,
      importance: form.importance,
      tags: form.tags,
      summary: form.summary,
      detail: form.detail,
      order_index: Number(form.order_index) || 0,
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
  const childrenByParent = new Map<string, SettingItem[]>()
  const ids = new Set(items.map((item) => item.id))
  const roots: SettingItem[] = []

  for (const item of items) {
    if (!item.parent_id || !ids.has(item.parent_id)) {
      roots.push(item)
      continue
    }

    const children = childrenByParent.get(item.parent_id) ?? []
    children.push(item)
    childrenByParent.set(item.parent_id, children)
  }

  const sortItems = (left: SettingItem, right: SettingItem) =>
    left.order_index - right.order_index || left.title.localeCompare(right.title, 'zh-Hans-CN')

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
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="settings-page">
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
      <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewSetting">
        新建设定
      </button>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载设定集…</section>

    <section v-else class="settings-layout">
      <aside class="list-panel">
        <p class="boundary-card">这里保存的是本书内部设定。外部资料、灵感素材和参考内容后续将放入知识库模块。</p>

        <div class="filters">
          <input v-model="filters.keyword" type="search" placeholder="搜索标题、简介、详细设定或标签" />
          <select v-model="filters.item_type">
            <option value="">全部类型</option>
            <option v-for="itemType in itemTypes" :key="itemType" :value="itemType">
              {{ settingItemTypeLabels[itemType] }}
            </option>
          </select>
          <select v-model="filters.canon_status">
            <option value="">全部确认状态</option>
            <option v-for="status in canonStatuses" :key="status" :value="status">
              {{ settingCanonStatusLabels[status] }}
            </option>
          </select>
          <select v-model="filters.importance">
            <option value="">全部重要程度</option>
            <option v-for="importance in importances" :key="importance" :value="importance">
              {{ settingImportanceLabels[importance] }}
            </option>
          </select>
          <button class="secondary-button" type="button" :disabled="isSaving" @click="handleApplyFilters">
            筛选
          </button>
        </div>

        <p v-if="settings.length === 0" class="empty-state">暂无设定，请先新建设定。</p>

        <ul v-else class="setting-list">
          <li v-for="item in treeItems" :key="item.setting.id">
            <button
              class="setting-card"
              type="button"
              :class="{ active: selectedSetting?.id === item.setting.id }"
              :style="{ paddingLeft: `${12 + item.level * 18}px` }"
              @click="handleSelectSetting(item.setting)"
            >
              <span class="title">{{ item.setting.title }}</span>
              <span class="meta">
                {{ settingItemTypeLabels[item.setting.item_type] }} ·
                {{ settingCanonStatusLabels[item.setting.canon_status] }} ·
                {{ settingImportanceLabels[item.setting.importance] }}
              </span>
              <span v-if="item.setting.tags" class="tags">{{ item.setting.tags }}</span>
              <span class="summary">{{ item.setting.summary || '暂无简介' }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <form class="editor-panel" @submit.prevent="handleSaveSetting">
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
          <label>
            <span>类型</span>
            <select v-model="form.item_type">
              <option v-for="itemType in itemTypes" :key="itemType" :value="itemType">
                {{ settingItemTypeLabels[itemType] }}
              </option>
            </select>
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
          <label>
            <span>父级设定</span>
            <select v-model="form.parent_id">
              <option value="">无父级设定</option>
              <option v-for="setting in parentOptions" :key="setting.id" :value="setting.id">
                {{ setting.title }}
              </option>
            </select>
          </label>
          <label>
            <span>排序序号</span>
            <input v-model.number="form.order_index" type="number" min="0" />
          </label>
        </div>

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

        <footer class="editor-actions">
          <button
            class="secondary-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedSetting"
            @click="handleOpenGraphNode"
          >
            在关系图中查看
          </button>
          <button
            class="danger-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedSetting"
            @click="handleDeleteSetting"
          >
            删除设定
          </button>
          <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
            {{ isSaving ? '正在保存…' : '保存设定' }}
          </button>
        </footer>
      </form>
      <MaterialLinkPanel
        v-if="selectedSetting"
        :project-id="projectId"
        source-type="setting"
        :source-id="selectedSetting.id"
        :source-title="selectedSetting.title"
      />
    </section>
  </main>
</template>

<style scoped>
.settings-page {
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
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.project-title,
.boundary-note {
  margin: 0;
  color: #64748b;
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

.settings-layout {
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

.boundary-card {
  margin: 0 0 14px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 12px;
  background: #eff6ff;
  color: #1e40af;
  font-weight: 800;
  line-height: 1.7;
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
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.setting-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.title {
  font-size: 1rem;
  font-weight: 800;
}

.meta,
.tags,
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

.form-grid {
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
</style>

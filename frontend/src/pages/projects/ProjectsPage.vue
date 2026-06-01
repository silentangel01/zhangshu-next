<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import defaultBookCover from '@/assets/default-book-cover.svg'
import { getCloudAccountStatus } from '@/entities/cloud/api'
import type { CloudAccountStatus } from '@/entities/cloud/types'
import CloudAccountDialog from '@/features/cloud/CloudAccountDialog.vue'
import CloudProjectImportDialog from '@/features/cloud/CloudProjectImportDialog.vue'
import {
  createProject,
  deleteProject,
  deleteProjectCover,
  getProjectCoverUrl,
  listProjects,
  updateProject,
  uploadProjectCover,
} from '@/entities/project/api'
import type { CreateProjectPayload, Project, ProjectStatus, UpdateProjectPayload } from '@/entities/project/types'
import CreateProjectDialog from '@/features/projects/CreateProjectDialog.vue'
import EditProjectDialog from '@/features/projects/EditProjectDialog.vue'
import {
  collectProjectTags,
  countActiveFilters,
  filterProjects,
  sortProjects,
  type ProjectFilterState,
  type ProjectSortKey,
} from '@/features/projects/projectFilters'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const BUILTIN_TAGS = [
  '玄幻',
  '都市',
  '科幻',
  '悬疑',
  '历史',
  '仙侠',
  '奇幻',
  '群像',
  '长篇',
  '短篇',
]

const router = useRouter()
const route = useRoute()

const STATUS_LABELS: Record<string, string> = {
  planning: '筹备中',
  writing: '连载中',
  paused: '暂停',
  completed: '已完结',
  archived: '已归档',
}

const STATUS_OPTIONS: { value: ProjectStatus | ''; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'planning', label: '筹备中' },
  { value: 'writing', label: '连载中' },
  { value: 'paused', label: '暂停' },
  { value: 'completed', label: '已完结' },
  { value: 'archived', label: '已归档' },
]

const SORT_OPTIONS: { value: ProjectSortKey; label: string }[] = [
  { value: 'updated_at', label: '最近更新' },
  { value: 'created_at', label: '创建时间' },
  { value: 'title', label: '书名' },
  { value: 'author', label: '作者' },
]

const projects = ref<Project[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showCreateDialog = ref(false)
const editingProject = ref<Project | null>(null)
const isFilterPanelOpen = ref(false)
const showCloudDialog = ref(false)
const showImportDialog = ref(false)
const showImportMenu = ref(false)
const cloudAccountStatus = ref<CloudAccountStatus | null>(null)

const searchKeyword = ref('')
const filterState = ref<ProjectFilterState>({ keyword: '', status: '', tag: '' })
const sortKey = ref<ProjectSortKey>('updated_at')

const hasProjects = computed(() => projects.value.length > 0)
const activeFilterCount = computed(() => countActiveFilters(filterState.value))

const tagSuggestions = computed(() => collectProjectTags(projects.value, BUILTIN_TAGS))

const displayedProjects = computed(() => {
  const withKeyword = { ...filterState.value, keyword: searchKeyword.value }
  const filtered = filterProjects(projects.value, withKeyword)
  return sortProjects(filtered, sortKey.value)
})

onMounted(() => {
  void refreshProjects()
  void loadCloudStatus()
  document.addEventListener('click', handleOutsideClick)

  // Auto-open cloud dialog if navigated with ?openCloudDialog=1
  if (route.query.openCloudDialog === '1') {
    showCloudDialog.value = true
    // Clean up the query param to avoid re-opening on refresh
    router.replace({ path: '/projects', query: {} })
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})

function handleOutsideClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.import-dropdown')) {
    showImportMenu.value = false
  }
}

function toggleImportMenu(event: MouseEvent) {
  event.stopPropagation()
  showImportMenu.value = !showImportMenu.value
}

function handleFileImport() {
  showImportMenu.value = false
  router.push('/imports')
}

function handleCloudImport() {
  showImportMenu.value = false
  showImportDialog.value = true
}

async function loadCloudStatus() {
  try {
    cloudAccountStatus.value = await getCloudAccountStatus()
  } catch {
    // Cloud not configured — silently ignore.
  }
}

async function refreshProjects() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    projects.value = await listProjects()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载项目失败。')
  } finally {
    isLoading.value = false
  }
}

function getCoverUrl(project: Project): string | null {
  if (!project.cover_image_path) {
    return null
  }
  return getProjectCoverUrl(project.id, project.version)
}

function handleClearFilters() {
  filterState.value = { keyword: '', status: '', tag: '' }
  searchKeyword.value = ''
  isFilterPanelOpen.value = false
}

async function handleCreate(payload: { project: CreateProjectPayload; coverFile: File | null }) {
  isSaving.value = true
  errorMessage.value = ''

  try {
    const created = await createProject(payload.project)

    if (payload.coverFile) {
      try {
        await uploadProjectCover(created.id, payload.coverFile)
      } catch {
        errorMessage.value = `项目"${created.title}"已创建，但封面上传失败。`
      }
    }

    showCreateDialog.value = false
    await refreshProjects()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '新建项目失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleEdit(payload: UpdateProjectPayload) {
  if (!editingProject.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await updateProject(editingProject.value.id, payload)
    editingProject.value = null
    await refreshProjects()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '更新项目失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleEditCoverUpload(file: File) {
  if (!editingProject.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await uploadProjectCover(editingProject.value.id, file)
    await refreshProjects()
    const updated = projects.value.find((p) => p.id === editingProject.value!.id)
    if (updated) {
      editingProject.value = updated
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '封面上传失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleEditCoverDelete() {
  if (!editingProject.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteProjectCover(editingProject.value.id)
    await refreshProjects()
    const updated = projects.value.find((p) => p.id === editingProject.value!.id)
    if (updated) {
      editingProject.value = updated
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除封面失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleDelete(project: Project) {
  const confirmed = window.confirm(`确定要删除项目"${project.title}"吗？`)

  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteProject(project.id)
    await refreshProjects()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除项目失败。')
  } finally {
    isSaving.value = false
  }
}

function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function handleCloudAccountClick() {
  if (cloudAccountStatus.value?.logged_in) {
    router.push('/account')
  } else {
    showCloudDialog.value = true
  }
}
</script>

<template>
  <main class="projects-page">
    <header class="page-header">
      <div>
        <h1>我的作品</h1>
      </div>
      <div class="header-actions">
        <button
          class="secondary-link cloud-account-button"
          type="button"
          @click="handleCloudAccountClick"
        >
          {{ cloudAccountStatus?.logged_in ? cloudAccountStatus.email ?? '云账户' : '云账户' }}
        </button>
        <div class="import-dropdown">
          <button
            class="secondary-link import-trigger"
            type="button"
            @click="toggleImportMenu"
          >
            导入
            <span class="caret" aria-hidden="true">▾</span>
          </button>
          <ul v-show="showImportMenu" class="import-menu">
            <li>
              <button type="button" @click="handleFileImport">从文件导入</button>
            </li>
            <li v-if="cloudAccountStatus?.logged_in">
              <button type="button" @click="handleCloudImport">从云端恢复</button>
            </li>
          </ul>
        </div>
        <RouterLink class="secondary-link" to="/backup">备份恢复</RouterLink>
        <button class="primary-button" type="button" :disabled="isSaving" @click="showCreateDialog = true">
          新建作品
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="hasProjects" class="projects-toolbar">
      <div class="toolbar-search">
        <input
          v-model="searchKeyword"
          type="search"
          placeholder="搜索书名、作者、简介或标签"
          class="search-input"
        />
      </div>
      <div class="toolbar-controls">
        <div class="filter-menu">
          <button
            class="filter-button"
            type="button"
            :class="{ active: isFilterPanelOpen || activeFilterCount > 0 }"
            :aria-expanded="isFilterPanelOpen"
            aria-controls="projects-filter-panel"
            @click="isFilterPanelOpen = !isFilterPanelOpen"
          >
            筛选{{ activeFilterCount > 0 ? `（${activeFilterCount}）` : '' }}
          </button>
          <div v-if="isFilterPanelOpen" id="projects-filter-panel" class="filter-panel">
            <label class="filter-field">
              <span>写作状态</span>
              <select v-model="filterState.status">
                <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label class="filter-field">
              <span>标签</span>
              <select v-model="filterState.tag">
                <option value="">全部标签</option>
                <option v-for="tag in tagSuggestions" :key="tag" :value="tag">{{ tag }}</option>
              </select>
            </label>
            <div class="filter-actions">
              <button class="secondary-button" type="button" @click="handleClearFilters">清空</button>
              <button class="primary-button" type="button" @click="isFilterPanelOpen = false">确定</button>
            </div>
          </div>
        </div>
        <label class="sort-control">
          <span>排序</span>
          <select v-model="sortKey">
            <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </label>
      </div>
    </section>

    <section class="content-panel" aria-live="polite">
      <div v-if="isLoading" class="state-message">正在加载……</div>

      <div v-else-if="!hasProjects" class="empty-state">
        <h2>暂无作品</h2>
        <p>还没有作品。新建作品后开始写第一章。</p>
      </div>

      <div v-else-if="displayedProjects.length === 0" class="empty-state compact">
        <p>没有匹配的作品，调整搜索或筛选条件。</p>
      </div>

      <div v-else class="book-grid">
        <article v-for="project in displayedProjects" :key="project.id" class="book-card">
          <div class="book-cover">
            <img
              :src="getCoverUrl(project) || defaultBookCover"
              :alt="`${project.title} 封面`"
            />
          </div>

          <div class="book-info">
            <header class="book-header">
              <h2>{{ project.title }}</h2>
              <span class="status-badge" :class="`status-${project.status}`">
                {{ getStatusLabel(project.status) }}
              </span>
            </header>

            <p class="book-author">{{ project.author || '未设置作者' }}</p>
            <p class="book-genre">{{ project.genre || '未设置类型' }}</p>

            <div v-if="project.tags.length > 0" class="book-tags">
              <span v-for="tag in project.tags.slice(0, 6)" :key="tag" class="book-tag">
                {{ tag }}
              </span>
              <span v-if="project.tags.length > 6" class="book-tag more">
                +{{ project.tags.length - 6 }}
              </span>
            </div>

            <p class="book-summary">{{ project.summary || '暂无简介。' }}</p>

            <footer class="book-footer">
              <span class="book-updated">更新于 {{ formatDateTime(project.updated_at) }}</span>
              <div class="book-actions">
                <RouterLink class="open-link" :to="`/projects/${project.id}`">打开</RouterLink>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="isSaving"
                  @click="editingProject = project"
                >
                  编辑
                </button>
                <button
                  class="danger-button"
                  type="button"
                  :disabled="isSaving"
                  @click="handleDelete(project)"
                >
                  删除
                </button>
              </div>
            </footer>
          </div>
        </article>
      </div>
    </section>

    <CreateProjectDialog
      v-if="showCreateDialog"
      :tag-suggestions="tagSuggestions"
      :default-cover-url="defaultBookCover"
      @close="showCreateDialog = false"
      @submit="handleCreate"
    />

    <EditProjectDialog
      v-if="editingProject"
      :project="editingProject"
      :tag-suggestions="tagSuggestions"
      :default-cover-url="defaultBookCover"
      @close="editingProject = null"
      @submit="handleEdit"
      @upload-cover="handleEditCoverUpload"
      @delete-cover="handleEditCoverDelete"
    />

    <CloudAccountDialog
      v-if="showCloudDialog"
      @close="showCloudDialog = false; loadCloudStatus()"
    />

    <CloudProjectImportDialog
      v-if="showImportDialog"
      @close="showImportDialog = false"
      @imported="refreshProjects()"
    />
  </main>
</template>

<style scoped>
.projects-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24px 32px;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 1120px;
  margin: 0 auto 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.3;
}

.content-panel,
.error-banner {
  max-width: 1120px;
  margin: 0 auto;
}

.content-panel {
  min-height: 320px;
}

.error-banner {
  box-sizing: border-box;
  margin-bottom: 12px;
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-md);
  padding: 10px 12px;
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-weight: 600;
  font-size: 0.88rem;
}

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 240px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
}

.empty-state {
  align-content: center;
  gap: 8px;
  text-align: center;
}

.empty-state h2,
.empty-state p {
  margin: 0;
}

.empty-state h2 {
  color: var(--zs-color-text);
  font-size: 1.05rem;
  font-weight: 700;
}

.book-grid {
  display: grid;
  gap: 16px;
}

.book-card {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 16px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 16px;
  background: var(--zs-color-surface);
}

.book-cover {
  width: 88px;
  aspect-ratio: 3 / 4.2;
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
  border: 1px solid var(--zs-color-border-soft);
  background: var(--zs-color-surface-soft);
  flex-shrink: 0;
}

.book-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.book-info {
  display: grid;
  gap: 6px;
  align-content: start;
  min-width: 0;
}

.book-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.book-header h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.3;
}

.status-badge {
  flex: 0 0 auto;
  border-radius: var(--zs-radius-sm);
  padding: 2px 8px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.status-planning {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.status-writing {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.status-paused {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.status-completed {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.status-archived {
  background: var(--zs-color-surface-muted);
  color: var(--zs-color-text-muted);
}

.book-author {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-weight: 600;
}

.book-genre {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.book-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.book-tag {
  border-radius: var(--zs-radius-sm);
  padding: 2px 6px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  font-weight: 600;
  border: 1px solid var(--zs-color-border-soft);
}

.book-tag.more {
  background: var(--zs-color-surface-muted);
  color: var(--zs-color-text-faint);
}

.book-summary {
  margin: 4px 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
}

.book-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
  color: var(--zs-color-text-faint);
  font-size: 0.82rem;
}

.book-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.open-link {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  box-sizing: border-box;
  border-radius: var(--zs-radius-sm);
  padding: 0 10px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-weight: 600;
  font-size: 0.82rem;
  text-decoration: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-weight: 600;
  font-size: 0.84rem;
  text-decoration: none;
}

.cloud-account-button {
  cursor: pointer;
  font: inherit;
}

.import-dropdown {
  position: relative;
}

.import-trigger {
  cursor: pointer;
  font: inherit;
  gap: 4px;
}

.import-trigger .caret {
  font-size: 0.7em;
  opacity: 0.6;
}

.import-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 100;
  min-width: 140px;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  background: var(--zs-color-surface);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.import-menu li button {
  display: block;
  width: 100%;
  min-height: 32px;
  border: none;
  border-radius: 0;
  padding: 0 12px;
  background: none;
  color: var(--zs-color-text);
  font: inherit;
  font-weight: 400;
  font-size: 0.84rem;
  text-align: left;
  cursor: pointer;
}

.import-menu li button:hover {
  background: var(--zs-color-surface-soft, #f5f5f5);
}

button {
  min-height: 30px;
  border-radius: var(--zs-radius-sm);
  border: 1px solid transparent;
  padding: 0 10px;
  font: inherit;
  font-weight: 600;
  font-size: 0.84rem;
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

.projects-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  max-width: 1120px;
  margin: 0 auto 16px;
}

.toolbar-search {
  flex: 1 1 280px;
  min-width: 0;
}

.search-input {
  width: 100%;
  box-sizing: border-box;
  min-height: 32px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.88rem;
}

.search-input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-focus);
}

.toolbar-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-menu {
  position: relative;
}

.filter-button {
  min-height: 32px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
}

.filter-button.active {
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
  border-radius: var(--zs-radius-md);
  padding: 14px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.filter-field {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
}

.filter-field select {
  width: 100%;
  min-height: 30px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

.filter-actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.sort-control {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-weight: 600;
}

.sort-control select {
  min-height: 32px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

.empty-state.compact {
  min-height: 140px;
}

/* Reserve space for the fixed top-right bar (notification bell + theme switcher)
 * at viewports where overlap can occur. The top bar is ~220px wide and fixed at
 * the viewport right edge. At wide viewports (>1600px) the centered content
 * clears it naturally; at narrow viewports (<=720px) the bar moves to bottom. */
@media (min-width: 721px) and (max-width: 1600px) {
  .page-header {
    padding-right: var(--top-bar-width, 220px);
  }
}

@media (max-width: 720px) {
  .projects-page {
    padding: 16px 12px;
  }

  .page-header,
  .header-actions,
  .book-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .book-card {
    grid-template-columns: 72px 1fr;
    gap: 12px;
    padding: 12px;
  }

  .book-cover {
    width: 72px;
  }

  .primary-button,
  .secondary-link {
    justify-content: center;
    width: 100%;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import {
  createChapter,
  deleteChapter,
  getChapter,
  listChapters,
  reorderChapters,
  updateChapter,
} from '@/entities/chapter/api'
import {
  createChapterVersion,
  getChapterVersion,
  listChapterVersions,
  restoreChapterVersion,
} from '@/entities/chapter-version/api'
import type {
  ChapterVersionDetail,
  ChapterVersionListItem,
} from '@/entities/chapter-version/types'
import type {
  Chapter,
  CreateChapterPayload,
  ReorderChaptersPayload,
  UpdateChapterMetadataPayload,
} from '@/entities/chapter/types'
import defaultBookCover from '@/assets/default-book-cover.svg'
import { getProject, getProjectCoverUrl } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { createVolume, deleteVolume, listVolumes, updateVolume } from '@/entities/volume/api'
import type { CreateVolumePayload, UpdateVolumePayload, Volume } from '@/entities/volume/types'
import ChapterTree from '@/features/chapters/ChapterTree.vue'
import ChapterEditor from '@/features/chapters/ChapterEditor.vue'
import ChapterVersionPreviewDialog from '@/features/chapters/ChapterVersionPreviewDialog.vue'
import CreateChapterDialog from '@/features/chapters/CreateChapterDialog.vue'
import EditChapterDialog from '@/features/chapters/EditChapterDialog.vue'
import { clearRecoveryDraft } from '@/features/chapters/recoveryDraft'
import AppSettingsDialog from '@/features/app-config/AppSettingsDialog.vue'
import CreateVolumeDialog from '@/features/volumes/CreateVolumeDialog.vue'
import EditVolumeDialog from '@/features/volumes/EditVolumeDialog.vue'
import WritingAidPanel from '@/features/writing/WritingAidPanel.vue'
import CloudSyncStatusIndicator from '@/features/cloud/CloudSyncStatusIndicator.vue'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const route = useRoute()

const project = ref<Project | null>(null)
const volumes = ref<Volume[]>([])
const chapters = ref<Chapter[]>([])
const chapterVersions = ref<ChapterVersionListItem[]>([])
const previewVersion = ref<ChapterVersionDetail | null>(null)
const selectedChapter = ref<Chapter | null>(null)
const editingVolume = ref<Volume | null>(null)
const editingChapter = ref<Chapter | null>(null)
const createChapterVolumeId = ref<string | null>(null)
const chapterEditor = ref<InstanceType<typeof ChapterEditor> | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const isChapterLoading = ref(false)
const isEditorDirty = ref(false)
const isVersionLoading = ref(false)
const isVersionBusy = ref(false)
const errorMessage = ref('')
const versionErrorMessage = ref('')
const versionMessage = ref('')
const treeMessage = ref('')
const treeMessageTone = ref<'success' | 'warning'>('success')
const showCreateVolumeDialog = ref(false)
const showCreateChapterDialog = ref(false)
const showAppSettings = ref(false)
const rightAidTab = ref<WritingAidTab | null>(null)
const isLeftPanelCollapsed = ref(false)
const isRightPanelCollapsed = ref(false)
const isWorkspaceTransitionReady = ref(false)

type WritingAidTab = 'outline' | 'characters' | 'settings' | 'graph' | 'timeline' | 'foreshadowing' | 'reminders' | 'versions'

interface WorkspaceViewState {
  selectedChapterId: string | null
  rightAidTab: WritingAidTab | null
  leftPanelCollapsed: boolean
  rightPanelCollapsed: boolean
}

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
  void loadProjectWorkspace()
})

watch(projectId, () => {
  selectedChapter.value = null
  chapterVersions.value = []
  previewVersion.value = null
  isEditorDirty.value = false
  treeMessage.value = ''
  createChapterVolumeId.value = null
  isWorkspaceTransitionReady.value = false
  void loadProjectWorkspace()
})

async function loadProjectWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  isWorkspaceTransitionReady.value = false
  errorMessage.value = ''

  try {
    const [projectDetail, projectVolumes, projectChapters] = await Promise.all([
      getProject(projectId.value),
      listVolumes(projectId.value),
      listChapters(projectId.value),
    ])

    project.value = projectDetail
    volumes.value = projectVolumes
    chapters.value = projectChapters
    await restoreWorkspaceViewState()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载项目详情失败。')
  } finally {
    isLoading.value = false
    window.requestAnimationFrame(() => {
      isWorkspaceTransitionReady.value = true
    })
  }
}

async function refreshVolumesAndChapters() {
  if (!projectId.value) {
    return
  }

  const [projectVolumes, projectChapters] = await Promise.all([
    listVolumes(projectId.value),
    listChapters(projectId.value),
  ])

  volumes.value = projectVolumes
  chapters.value = projectChapters
  reconcileStoredSelectedChapter()
}

async function restoreWorkspaceViewState() {
  const state = readValidWorkspaceViewState()
  rightAidTab.value = state.rightAidTab
  isLeftPanelCollapsed.value = state.leftPanelCollapsed
  isRightPanelCollapsed.value = state.rightPanelCollapsed

  if (!state.selectedChapterId) {
    return
  }

  const chapter = chapters.value.find((item) => item.id === state.selectedChapterId)
  if (!chapter) {
    saveWorkspaceViewState({ selectedChapterId: null })
    return
  }

  await handleSelectChapter(chapter)
}

function reconcileStoredSelectedChapter() {
  const state = readValidWorkspaceViewState()
  if (!state.selectedChapterId) {
    return
  }
  const stillExists = chapters.value.some((chapter) => chapter.id === state.selectedChapterId)
  if (!stillExists) {
    saveWorkspaceViewState({ selectedChapterId: null })
  }
}

function saveWorkspaceViewState(patch: Partial<WorkspaceViewState>) {
  const current = readValidWorkspaceViewState()
  safeWriteJson(workspaceStorageKey.value, {
    selectedChapterId: Object.prototype.hasOwnProperty.call(patch, 'selectedChapterId')
      ? patch.selectedChapterId ?? null
      : current.selectedChapterId,
    rightAidTab: Object.prototype.hasOwnProperty.call(patch, 'rightAidTab')
      ? patch.rightAidTab ?? null
      : current.rightAidTab,
    leftPanelCollapsed: Object.prototype.hasOwnProperty.call(patch, 'leftPanelCollapsed')
      ? Boolean(patch.leftPanelCollapsed)
      : current.leftPanelCollapsed,
    rightPanelCollapsed: Object.prototype.hasOwnProperty.call(patch, 'rightPanelCollapsed')
      ? Boolean(patch.rightPanelCollapsed)
      : current.rightPanelCollapsed,
  } satisfies WorkspaceViewState)
}

function readValidWorkspaceViewState(): WorkspaceViewState {
  const state = safeReadJson<Partial<WorkspaceViewState> | null>(workspaceStorageKey.value, null)
  const validTab = isWritingAidTab(state?.rightAidTab) ? state.rightAidTab : null
  return {
    selectedChapterId: typeof state?.selectedChapterId === 'string' ? state.selectedChapterId : null,
    rightAidTab: validTab,
    leftPanelCollapsed: typeof state?.leftPanelCollapsed === 'boolean' ? state.leftPanelCollapsed : false,
    rightPanelCollapsed: typeof state?.rightPanelCollapsed === 'boolean' ? state.rightPanelCollapsed : false,
  }
}

function isWritingAidTab(value: unknown): value is WritingAidTab {
  return value === 'outline'
    || value === 'characters'
    || value === 'settings'
    || value === 'graph'
    || value === 'timeline'
    || value === 'foreshadowing'
    || value === 'reminders'
    || value === 'versions'
}

function handleRightAidTabChanged(tab: WritingAidTab) {
  rightAidTab.value = tab
  saveWorkspaceViewState({ rightAidTab: tab })
}

function toggleLeftPanel() {
  isLeftPanelCollapsed.value = !isLeftPanelCollapsed.value
  saveWorkspaceViewState({ leftPanelCollapsed: isLeftPanelCollapsed.value })
}

function toggleRightPanel() {
  isRightPanelCollapsed.value = !isRightPanelCollapsed.value
  saveWorkspaceViewState({ rightPanelCollapsed: isRightPanelCollapsed.value })
}

async function handleCreateVolume(payload: CreateVolumePayload) {
  if (!projectId.value) {
    return
  }

  await saveChange(async () => {
    await createVolume(projectId.value, payload)
    showCreateVolumeDialog.value = false
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '新建分卷失败。')
}

async function handleEditVolume(payload: UpdateVolumePayload) {
  const volume = editingVolume.value

  if (!volume) {
    return
  }

  await saveChange(async () => {
    await updateVolume(volume.id, payload)
    editingVolume.value = null
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '更新分卷失败。')
}

async function handleDeleteVolume(volume: Volume) {
  const confirmed = window.confirm(`确定要删除分卷“${volume.title}”吗？`)

  if (!confirmed) {
    return
  }

  await saveChange(async () => {
    await deleteVolume(volume.id)
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '删除分卷失败。')
}

async function handleCreateChapter(payload: CreateChapterPayload) {
  if (!projectId.value) {
    return
  }

  await saveChange(async () => {
    await createChapter(projectId.value, payload)
    showCreateChapterDialog.value = false
    createChapterVolumeId.value = null
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '新建章节失败。')
}

function handleCreateVolumeRequest() {
  showCreateVolumeDialog.value = true
}

function handleCreateChapterRequest(volumeId: string | null) {
  createChapterVolumeId.value = volumeId
  showCreateChapterDialog.value = true
}

async function handleEditChapter(payload: UpdateChapterMetadataPayload) {
  const chapter = editingChapter.value

  if (!chapter) {
    return
  }

  await saveChange(async () => {
    const currentChapter = await getChapter(chapter.id)
    const updatedChapter = await updateChapter(chapter.id, {
      title: payload.title,
      content: currentChapter.content,
      volume_id: payload.volume_id,
      order_index: payload.order_index,
      status: payload.status,
    })

    editingChapter.value = null
    selectedChapter.value = selectedChapter.value?.id === updatedChapter.id ? updatedChapter : selectedChapter.value
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '更新章节信息失败。')
}

async function handleDeleteChapter(chapter: Chapter) {
  const confirmed = window.confirm(`确定要删除章节“${chapter.title}”吗？`)

  if (!confirmed) {
    return
  }

  await saveChange(async () => {
    await deleteChapter(chapter.id)
    if (selectedChapter.value?.id === chapter.id) {
      selectedChapter.value = null
      chapterVersions.value = []
      previewVersion.value = null
      versionMessage.value = ''
      versionErrorMessage.value = ''
      isEditorDirty.value = false
      saveWorkspaceViewState({ selectedChapterId: null })
    }
    await refreshVolumesAndChapters()
    cloudSyncManager.notifyDirty(projectId.value)
  }, '删除章节失败。')
}

async function handleReorderChapters(payload: ReorderChaptersPayload) {
  if (!projectId.value) {
    return
  }

  treeMessage.value = ''

  await saveChange(async () => {
    const result = await reorderChapters(projectId.value, payload)
    await refreshVolumesAndChapters()

    if (result.warnings.length > 0) {
      treeMessageTone.value = 'warning'
      treeMessage.value = result.warnings.join(' ')
    } else {
      treeMessageTone.value = 'success'
      treeMessage.value = '章节顺序已更新'
    }
    cloudSyncManager.notifyDirty(projectId.value)
  }, '章节移动失败，请重试')
}

async function handleSelectChapter(chapter: Chapter) {
  if (chapter.id === selectedChapter.value?.id) {
    return
  }

  if (isEditorDirty.value) {
    const saveFirst = window.confirm(
      '当前章节有未保存的更改，是否在切换前保存？\n\n点击"确定"保存后切换，点击"取消"放弃更改。',
    )

    if (saveFirst) {
      try {
        await chapterEditor.value?.saveNow?.()
      } catch {
        const force = window.confirm('保存失败，是否仍然切换章节？（未保存的更改将丢失）')
        if (!force) return
        chapterEditor.value?.cancelPendingAutosave()
      }
    } else {
      chapterEditor.value?.cancelPendingAutosave()
    }
  }

  isChapterLoading.value = true
  errorMessage.value = ''
  versionMessage.value = ''
  versionErrorMessage.value = ''
  chapterVersions.value = []
  previewVersion.value = null

  try {
    selectedChapter.value = await getChapter(chapter.id)
    await loadChapterVersions(chapter.id)
    isEditorDirty.value = false
    saveWorkspaceViewState({ selectedChapterId: chapter.id })
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载章节失败。')
  } finally {
    isChapterLoading.value = false
  }
}

async function handleChapterSaved(chapter: Chapter) {
  try {
    selectedChapter.value = await getChapter(chapter.id)
    await refreshVolumesAndChapters()
    await loadChapterVersions(chapter.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '章节已保存，但刷新失败。')
  }
}

async function loadChapterVersions(chapterId: string) {
  isVersionLoading.value = true
  versionErrorMessage.value = ''

  try {
    chapterVersions.value = await listChapterVersions(chapterId)
  } catch (error) {
    versionErrorMessage.value = getErrorMessage(error, '加载版本历史失败。')
  } finally {
    isVersionLoading.value = false
  }
}

async function handleCreateVersionSnapshot() {
  const chapter = selectedChapter.value
  if (!chapter) {
    return
  }

  isVersionBusy.value = true
  versionErrorMessage.value = ''
  versionMessage.value = ''

  try {
    await createChapterVersion(chapter.id, {
      source: 'manual',
      note: '用户手动创建版本',
    })
    await loadChapterVersions(chapter.id)
    versionMessage.value = '版本快照已创建。'
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    versionErrorMessage.value = getErrorMessage(error, '创建版本快照失败。')
  } finally {
    isVersionBusy.value = false
  }
}

async function handleViewVersion(versionId: string) {
  isVersionBusy.value = true
  versionErrorMessage.value = ''

  try {
    previewVersion.value = await getChapterVersion(versionId)
  } catch (error) {
    versionErrorMessage.value = getErrorMessage(error, '加载版本详情失败。')
  } finally {
    isVersionBusy.value = false
  }
}

async function handleRestoreVersion(versionId: string) {
  const chapter = selectedChapter.value
  if (!chapter) {
    return
  }

  const confirmed = window.confirm(
    '确认恢复此版本吗？当前正文会被覆盖，但系统会先创建恢复前备份。',
  )
  if (!confirmed) {
    return
  }

  chapterEditor.value?.cancelPendingAutosave()
  isVersionBusy.value = true
  versionErrorMessage.value = ''
  versionMessage.value = ''

  try {
    const restoredChapter = await restoreChapterVersion(chapter.id, versionId)
    clearRecoveryDraft(chapter.id)
    selectedChapter.value = await getChapter(restoredChapter.id)
    isEditorDirty.value = false
    previewVersion.value = null
    await refreshVolumesAndChapters()
    await loadChapterVersions(restoredChapter.id)
    versionMessage.value = '版本恢复成功。'
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    versionErrorMessage.value = getErrorMessage(error, '版本恢复失败。')
  } finally {
    isVersionBusy.value = false
  }
}

async function saveChange(action: () => Promise<void>, fallback: string) {
  isSaving.value = true
  errorMessage.value = ''

  try {
    await action()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, fallback)
  } finally {
    isSaving.value = false
  }
}

const STATUS_LABELS: Record<string, string> = {
  planning: '筹备中',
  writing: '连载中',
  paused: '暂停',
  completed: '已完结',
  archived: '已归档',
}

function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

const projectCoverUrl = computed<string | null>(() => {
  if (!project.value?.cover_image_path) {
    return null
  }
  return getProjectCoverUrl(project.value.id, project.value.version)
})

function getErrorMessage(error: unknown, fallback: string): string {
  void error
  return fallback
}

</script>

<template>
  <main class="project-detail-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" to="/projects">返回项目列表</RouterLink>
        <p class="eyebrow">写作工作区</p>
      </div>
      <div class="header-actions">
        <CloudSyncStatusIndicator />
        <RouterLink class="toolbar-link" :to="`/projects/${projectId}/search`">搜索</RouterLink>
        <RouterLink class="toolbar-link" :to="`/projects/${projectId}/review`">检查</RouterLink>
        <RouterLink class="toolbar-link" :to="`/projects/${projectId}/stats`">统计</RouterLink>
        <details class="more-menu">
          <summary>更多</summary>
          <div class="more-menu-list">
            <RouterLink :to="`/projects/${projectId}/outlines`">完整大纲</RouterLink>
            <RouterLink :to="`/projects/${projectId}/graph`">关系图</RouterLink>
            <RouterLink :to="`/projects/${projectId}/timeline`">时间轴</RouterLink>
            <RouterLink :to="`/projects/${projectId}/knowledge`">知识库</RouterLink>
            <RouterLink :to="`/projects/${projectId}/versions`">版本中心</RouterLink>
            <RouterLink to="/imports">导入导出</RouterLink>
            <RouterLink :to="`/projects/${projectId}/backup`">备份恢复</RouterLink>
            <button type="button" @click="showAppSettings = true">应用设置</button>
          </div>
        </details>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="isLoading" class="state-message">正在加载项目工作区……</section>

    <section
      v-else
      class="workspace-layout"
      :class="{
        'left-collapsed': isLeftPanelCollapsed,
        'right-collapsed': isRightPanelCollapsed,
        'transition-ready': isWorkspaceTransitionReady,
      }"
    >
      <aside class="sidebar" :class="{ collapsed: isLeftPanelCollapsed }">
        <button
          type="button"
          class="collapse-tab"
          :aria-label="isLeftPanelCollapsed ? '展开章节栏' : '收起章节栏'"
          @click="toggleLeftPanel"
        >
          {{ isLeftPanelCollapsed ? '展开章节' : '收起' }}
        </button>
        <div class="panel-content sidebar-content" :class="{ hidden: isLeftPanelCollapsed }" :aria-hidden="isLeftPanelCollapsed">
          <ChapterTree
            :project-title="project?.title || '作品标题'"
            :volumes="sortedVolumes"
            :chapters="sortedChapters"
            :selected-chapter-id="selectedChapter?.id ?? null"
            :is-reordering="isSaving"
            @select-chapter="handleSelectChapter"
            @create-volume="handleCreateVolumeRequest"
            @create-chapter="handleCreateChapterRequest"
            @edit-volume="editingVolume = $event"
            @delete-volume="handleDeleteVolume"
            @edit-chapter="editingChapter = $event"
            @delete-chapter="handleDeleteChapter"
            @reorder-chapters="handleReorderChapters"
          />
          <p v-if="treeMessage" class="tree-message" :class="treeMessageTone">{{ treeMessage }}</p>
        </div>
      </aside>

      <section class="detail-panel">
        <article v-if="selectedChapter" class="chapter-preview">
          <div v-if="isChapterLoading" class="chapter-loading">正在加载章节……</div>

          <ChapterEditor
            v-else
            ref="chapterEditor"
            :chapter="selectedChapter"
            @dirty-change="isEditorDirty = $event"
            @saved="handleChapterSaved"
          />

        </article>

        <article v-else class="project-summary">
          <header class="panel-header">
            <div>
              <p class="eyebrow">项目概览</p>
              <h2>{{ project?.title || '项目' }}</h2>
            </div>
            <div class="panel-badges">
              <span v-if="project" class="status-pill" :class="`status-${project.status}`">
                {{ getStatusLabel(project.status) }}
              </span>
              <span class="status-pill">未选择章节</span>
            </div>
          </header>

          <div v-if="project" class="summary-cover-row">
            <div class="summary-cover">
              <img
                :src="projectCoverUrl || defaultBookCover"
                :alt="`${project.title} 封面`"
              />
            </div>
            <dl class="metadata-grid">
              <div>
                <dt>作者</dt>
                <dd>{{ project.author || '未设置作者' }}</dd>
              </div>
              <div>
                <dt>类型</dt>
                <dd>{{ project.genre || '未设置类型' }}</dd>
              </div>
              <div>
                <dt>目标字数</dt>
                <dd>{{ project.target_word_count ? project.target_word_count.toLocaleString() : '未设置' }}</dd>
              </div>
              <div>
                <dt>更新时间</dt>
                <dd>{{ formatDateTime(project.updated_at) }}</dd>
              </div>
              <div>
                <dt>分卷</dt>
                <dd>{{ volumes.length }}</dd>
              </div>
              <div>
                <dt>章节</dt>
                <dd>{{ chapters.length }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="project?.tags.length" class="summary-tags">
            <span v-for="tag in project.tags" :key="tag" class="summary-tag">{{ tag }}</span>
          </div>

          <p class="summary-text">{{ project?.summary || '暂无项目简介。' }}</p>
        </article>
      </section>

      <aside class="aid-sidebar" :class="{ collapsed: isRightPanelCollapsed }">
        <button
          type="button"
          class="collapse-tab right"
          :aria-label="isRightPanelCollapsed ? '展开资料栏' : '收起资料栏'"
          @click="toggleRightPanel"
        >
          {{ isRightPanelCollapsed ? '展开资料' : '收起' }}
        </button>
        <div class="panel-content aid-content" :class="{ hidden: isRightPanelCollapsed }" :aria-hidden="isRightPanelCollapsed">
          <WritingAidPanel
            :project-id="projectId"
            :chapter-id="selectedChapter?.id ?? null"
            :initial-active-tab="rightAidTab"
            :versions="chapterVersions"
            :version-error-message="versionErrorMessage"
            :version-message="versionMessage"
            :version-is-loading="isVersionLoading"
            :version-is-busy="isVersionBusy"
            @active-tab-change="handleRightAidTabChanged"
            @create-snapshot="handleCreateVersionSnapshot"
            @view-version="handleViewVersion"
            @restore-version="handleRestoreVersion"
          />
        </div>
      </aside>
    </section>

    <CreateVolumeDialog
      v-if="showCreateVolumeDialog"
      @close="showCreateVolumeDialog = false"
      @submit="handleCreateVolume"
    />

    <EditVolumeDialog
      v-if="editingVolume"
      :volume="editingVolume"
      @close="editingVolume = null"
      @submit="handleEditVolume"
    />

    <CreateChapterDialog
      v-if="showCreateChapterDialog"
      :volumes="sortedVolumes"
      :initial-volume-id="createChapterVolumeId"
      @close="showCreateChapterDialog = false"
      @submit="handleCreateChapter"
    />

    <EditChapterDialog
      v-if="editingChapter"
      :chapter="editingChapter"
      :volumes="sortedVolumes"
      @close="editingChapter = null"
      @submit="handleEditChapter"
    />

    <ChapterVersionPreviewDialog
      v-if="previewVersion"
      :version="previewVersion"
      @close="previewVersion = null"
      @restore="handleRestoreVersion"
    />

    <AppSettingsDialog
      v-if="showAppSettings"
      @close="showAppSettings = false"
    />
  </main>
</template>

<style scoped>
.project-detail-page {
  min-height: 100vh;
  box-sizing: border-box;
  overflow-x: hidden;
  padding: var(--top-bar-clearance, var(--zs-space-6)) var(--zs-space-6) var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--zs-space-4);
  max-width: 1600px;
  margin: 0 auto var(--zs-space-4);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.eyebrow {
  margin: 0 0 var(--zs-space-1);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  line-height: 1.15;
}

h2 {
  font-size: 1.35rem;
}

.header-actions,
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-2);
}

.toolbar-link,
.more-menu > summary {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-3);
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.more-menu {
  position: relative;
}

.more-menu > summary {
  list-style: none;
  cursor: pointer;
}

.more-menu > summary::-webkit-details-marker {
  display: none;
}

.more-menu-list {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 20;
  display: grid;
  min-width: 150px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 6px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.more-menu-list a,
.more-menu-list button {
  border-radius: 6px;
  padding: 9px 10px;
  color: var(--zs-color-text);
  font-weight: 800;
  text-decoration: none;
}

.more-menu-list button {
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
  font-size: inherit;
  font-family: inherit;
}

.more-menu-list a:hover,
.more-menu-list a:focus-visible,
.more-menu-list button:hover,
.more-menu-list button:focus-visible {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-primary);
  outline: none;
}

.panel-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.error-banner,
.state-message,
.workspace-layout {
  max-width: 1600px;
  margin: 0 auto;
}

.error-banner {
  box-sizing: border-box;
  margin-bottom: var(--zs-space-4);
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-weight: 800;
}

.state-message {
  display: grid;
  place-items: center;
  min-height: 360px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
}

.workspace-layout {
  --left-panel-width: minmax(240px, 280px);
  --left-panel-collapsed-width: var(--zs-sidebar-collapsed-width);
  --right-panel-width: minmax(300px, 340px);
  --right-panel-collapsed-width: var(--zs-sidebar-collapsed-width);
  --workspace-transition-duration: var(--zs-duration-normal);
  --workspace-transition-easing: var(--zs-ease-standard);
  display: grid;
  grid-template-columns: var(--left-panel-width) minmax(var(--zs-writing-width-min), 1fr) var(--right-panel-width);
  gap: var(--zs-space-4);
  align-items: start;
  height: calc(100vh - 112px);
  min-height: 560px;
  min-width: 0;
}

.workspace-layout.transition-ready {
  transition: grid-template-columns var(--workspace-transition-duration) var(--workspace-transition-easing);
}

.workspace-layout.left-collapsed {
  grid-template-columns: var(--left-panel-collapsed-width) minmax(var(--zs-writing-width-min), 1fr) var(--right-panel-width);
}

.workspace-layout.right-collapsed {
  grid-template-columns: var(--left-panel-width) minmax(var(--zs-writing-width-min), 1fr) var(--right-panel-collapsed-width);
}

.workspace-layout.left-collapsed.right-collapsed {
  grid-template-columns: var(--left-panel-collapsed-width) minmax(var(--zs-writing-width-min), 1fr) var(--right-panel-collapsed-width);
}

.sidebar,
.detail-panel,
.aid-sidebar {
  min-width: 0;
  max-height: 100%;
  overflow: auto;
}

.sidebar {
  display: grid;
  gap: var(--zs-space-2);
  grid-template-rows: auto minmax(0, 1fr);
}

.aid-sidebar {
  display: grid;
  gap: var(--zs-space-2);
  grid-template-rows: auto minmax(0, 1fr);
}

.sidebar,
.aid-sidebar {
  position: relative;
  overflow: hidden;
  width: 100%;
  transition:
    opacity var(--workspace-transition-duration) var(--workspace-transition-easing),
    transform var(--workspace-transition-duration) var(--workspace-transition-easing);
}

.sidebar.collapsed,
.aid-sidebar.collapsed {
  place-items: start center;
  overflow: hidden;
}

.collapse-tab {
  justify-self: start;
  min-height: 30px;
  border-color: var(--zs-color-border);
  border-radius: var(--zs-radius-pill);
  padding: 0 var(--zs-space-2);
  background: color-mix(in srgb, var(--zs-color-surface) 84%, transparent);
  color: var(--zs-color-text-muted);
  box-shadow: none;
  transition:
    min-height var(--workspace-transition-duration) var(--workspace-transition-easing),
    padding var(--workspace-transition-duration) var(--workspace-transition-easing),
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
  white-space: nowrap;
}

.sidebar.collapsed .collapse-tab,
.aid-sidebar.collapsed .collapse-tab {
  justify-self: center;
  min-height: 112px;
  padding: 10px 3px;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.panel-content {
  min-width: 0;
  overflow: hidden;
  opacity: 1;
  transform: translateX(0);
  transition:
    opacity 160ms ease,
    transform var(--workspace-transition-duration) var(--workspace-transition-easing),
    visibility 0s linear 0s;
}

.workspace-layout.transition-ready .panel-content.hidden {
  transition:
    opacity 120ms ease,
    transform 160ms ease,
    visibility 0s linear 160ms;
}

.panel-content.hidden {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}

.sidebar .panel-content.hidden {
  transform: translateX(-8px);
}

.aid-sidebar .panel-content.hidden {
  transform: translateX(8px);
}

.tree-message {
  margin: -6px 2px 0;
  font-size: 0.84rem;
  line-height: 1.5;
}

.tree-message.success {
  color: var(--zs-color-primary);
}

.tree-message.warning {
  color: var(--zs-color-warning);
}

.detail-panel > article {
  min-height: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.detail-panel > .chapter-preview {
  display: flex;
  min-width: 0;
  overflow: auto;
}

.chapter-preview :deep(.chapter-editor) {
  width: 100%;
  min-width: 0;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: var(--zs-space-5) 0;
}

.metadata-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface-soft);
}

dt {
  margin: 0 0 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

dd {
  margin: 0;
  color: var(--zs-color-text);
  font-weight: 800;
}

.summary-text {
  margin: 0;
  color: var(--zs-color-text);
  line-height: 1.7;
  white-space: pre-wrap;
}

.summary-cover-row {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 16px;
  align-items: start;
}

.summary-cover {
  width: 90px;
  aspect-ratio: 3 / 4.2;
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
  border: 1px solid var(--zs-color-border-soft);
  background: var(--zs-color-surface-soft);
  flex-shrink: 0;
}

.summary-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.summary-tag {
  border-radius: 999px;
  padding: 3px 10px;
  background: var(--zs-color-info-soft, #eef2ff);
  color: var(--zs-color-info, #3730a3);
  font-size: 0.78rem;
  font-weight: 700;
}

.status-planning {
  background: var(--zs-color-info-soft, #f0f4ff);
  color: var(--zs-color-info, #3730a3);
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
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.chapter-loading {
  display: grid;
  place-items: center;
  min-height: 260px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
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

.status-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
  font-size: 0.78rem;
  font-weight: 800;
}

.version-message {
  margin: 12px 0 0;
  color: var(--zs-color-success);
  font-weight: 800;
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

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

@media (max-width: 1439px) {
  .project-detail-page {
    padding: var(--zs-space-4);
  }

  .workspace-layout {
    --left-panel-width: minmax(240px, 260px);
    --right-panel-width: minmax(300px, 320px);
    gap: var(--zs-space-3);
  }

  .toolbar-link,
  .more-menu > summary {
    padding: 0 var(--zs-space-2);
  }
}

@media (max-width: 1099px) {
  .project-detail-page {
    padding: var(--zs-space-3);
  }

  .page-header,
  .header-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .workspace-layout {
    --left-panel-width: minmax(220px, 240px);
    grid-template-columns: var(--left-panel-width) minmax(0, 1fr) var(--right-panel-collapsed-width);
    gap: var(--zs-space-2);
    height: calc(100vh - 160px);
    min-height: 520px;
    overflow-x: hidden;
  }

  .workspace-layout.left-collapsed {
    grid-template-columns: var(--left-panel-collapsed-width) minmax(0, 1fr) var(--right-panel-collapsed-width);
  }

  .workspace-layout.right-collapsed,
  .workspace-layout.left-collapsed.right-collapsed {
    grid-template-columns: var(--left-panel-width) minmax(0, 1fr) var(--right-panel-collapsed-width);
  }

  .workspace-layout.left-collapsed.right-collapsed {
    grid-template-columns: var(--left-panel-collapsed-width) minmax(0, 1fr) var(--right-panel-collapsed-width);
  }

  .aid-sidebar {
    place-items: start center;
    overflow: hidden;
  }

  .aid-sidebar .collapse-tab {
    justify-self: center;
    min-height: 112px;
    padding: 10px 3px;
    writing-mode: vertical-rl;
    text-orientation: mixed;
  }

  .aid-sidebar .panel-content {
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
    transform: translateX(8px);
  }

  .detail-panel > article {
    padding: var(--zs-space-3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-layout.transition-ready,
  .sidebar,
  .aid-sidebar,
  .collapse-tab,
  .panel-content,
  .workspace-layout.transition-ready .panel-content.hidden {
    transition: none;
  }
}
</style>

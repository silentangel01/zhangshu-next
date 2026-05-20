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
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { createVolume, deleteVolume, listVolumes, updateVolume } from '@/entities/volume/api'
import type { CreateVolumePayload, UpdateVolumePayload, Volume } from '@/entities/volume/types'
import ChapterTree from '@/features/chapters/ChapterTree.vue'
import ChapterEditor from '@/features/chapters/ChapterEditor.vue'
import ChapterVersionPreviewDialog from '@/features/chapters/ChapterVersionPreviewDialog.vue'
import CreateChapterDialog from '@/features/chapters/CreateChapterDialog.vue'
import EditChapterDialog from '@/features/chapters/EditChapterDialog.vue'
import { clearRecoveryDraft } from '@/features/chapters/recoveryDraft'
import CreateVolumeDialog from '@/features/volumes/CreateVolumeDialog.vue'
import EditVolumeDialog from '@/features/volumes/EditVolumeDialog.vue'
import WritingAidPanel from '@/features/writing/WritingAidPanel.vue'

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
  void loadProjectWorkspace()
})

async function loadProjectWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
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
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载项目详情失败。')
  } finally {
    isLoading.value = false
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
}

async function handleCreateVolume(payload: CreateVolumePayload) {
  if (!projectId.value) {
    return
  }

  await saveChange(async () => {
    await createVolume(projectId.value, payload)
    showCreateVolumeDialog.value = false
    await refreshVolumesAndChapters()
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
    }
    await refreshVolumesAndChapters()
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
  }, '章节移动失败，请重试')
}

async function handleSelectChapter(chapter: Chapter) {
  if (chapter.id === selectedChapter.value?.id) {
    return
  }

  if (isEditorDirty.value) {
    const confirmed = window.confirm('当前章节有未保存内容，是否放弃更改并切换章节？')

    if (!confirmed) {
      return
    }

    chapterEditor.value?.cancelPendingAutosave()
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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

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
        <p class="eyebrow">项目详情</p>
        <h1>{{ project?.title || '正在加载项目……' }}</h1>
      </div>
      <div class="header-actions">
        <RouterLink class="outline-link" :to="`/projects/${projectId}/outlines`">打开完整大纲</RouterLink>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="isLoading" class="state-message">正在加载项目工作区……</section>

    <section v-else class="workspace-layout">
      <aside class="sidebar">
        <nav class="project-nav" aria-label="项目导航">
          <RouterLink class="nav-link" to="/projects">项目列表</RouterLink>
          <RouterLink class="nav-link" :to="`/projects/${projectId}/outlines`">完整大纲</RouterLink>
          <RouterLink class="nav-link" :to="`/projects/${projectId}/characters`">人物库</RouterLink>
        </nav>
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
      </aside>

      <section class="detail-panel">
        <article v-if="selectedChapter" class="chapter-preview">
          <header class="panel-header">
            <div>
              <p class="eyebrow">当前章节</p>
              <h2>{{ selectedChapter.title }}</h2>
            </div>
          </header>

          <p class="chapter-hint">在右侧查看大纲、人物、设定、伏笔、时间轴和版本。</p>

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
              <span class="status-pill">未选择章节</span>
              <span v-if="project" class="version">v{{ project.version }}</span>
            </div>
          </header>

          <dl v-if="project" class="metadata-grid">
            <div>
              <dt>类型</dt>
              <dd>{{ project.genre || '未设置类型' }}</dd>
            </div>
            <div>
              <dt>更新时间</dt>
              <dd>{{ formatDate(project.updated_at) }}</dd>
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

          <p class="summary-text">{{ project?.summary || '暂无项目简介。' }}</p>
        </article>
      </section>

      <aside class="aid-sidebar">
        <WritingAidPanel
          :project-id="projectId"
          :chapter-id="selectedChapter?.id ?? null"
          :versions="chapterVersions"
          :version-error-message="versionErrorMessage"
          :version-message="versionMessage"
          :version-is-loading="isVersionLoading"
          :version-is-busy="isVersionBusy"
          @create-snapshot="handleCreateVersionSnapshot"
          @view-version="handleViewVersion"
          @restore-version="handleRestoreVersion"
        />
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
  </main>
</template>

<style scoped>
.project-detail-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: #f6f8fb;
  color: #111827;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto 22px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
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
h2 {
  margin: 0;
  line-height: 1.15;
}

h1 {
  font-size: 2rem;
}

h2 {
  font-size: 1.35rem;
}

.header-actions,
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.outline-link {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 14px;
  background: #ffffff;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
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
  margin-bottom: 16px;
  border: 1px solid #f4b4ad;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff1f0;
  color: #9f1c12;
  font-weight: 800;
}

.state-message {
  display: grid;
  place-items: center;
  min-height: 360px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
}

.workspace-layout {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(520px, 1fr) minmax(300px, 380px);
  gap: 18px;
  align-items: start;
  height: calc(100vh - 150px);
  min-height: 560px;
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
  gap: 14px;
}

.tree-message {
  margin: -6px 2px 0;
  font-size: 0.84rem;
  line-height: 1.5;
}

.tree-message.success {
  color: #2563eb;
}

.tree-message.warning {
  color: #b45309;
}

.detail-panel > article {
  min-height: 100%;
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.project-nav,
.sidebar-actions {
  display: grid;
  gap: 8px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  background: #fbfcfe;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 22px 0;
}

.metadata-grid div {
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
  text-transform: uppercase;
}

dd {
  margin: 0;
  color: #111827;
  font-weight: 800;
}

.summary-text {
  margin: 0;
  color: #374151;
  line-height: 1.7;
  white-space: pre-wrap;
}

.chapter-loading {
  display: grid;
  place-items: center;
  min-height: 260px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 16px;
  background: #fbfcfe;
  color: #64748b;
}

.chapter-hint {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.6;
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

.status-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: #ecfdf5;
  color: #047857;
  font-size: 0.78rem;
  font-weight: 800;
}

.version-message {
  margin: 12px 0 0;
  color: #047857;
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

@media (max-width: 860px) {
  .project-detail-page {
    padding: 24px 16px;
  }

  .page-header,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-layout {
    grid-template-columns: minmax(260px, 320px) minmax(520px, 1fr) minmax(300px, 380px);
    overflow-x: auto;
  }
}
</style>

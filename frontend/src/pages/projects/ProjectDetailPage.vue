<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import {
  createChapter,
  deleteChapter,
  getChapter,
  listChapters,
  updateChapter,
} from '@/entities/chapter/api'
import type {
  Chapter,
  CreateChapterPayload,
  UpdateChapterMetadataPayload,
} from '@/entities/chapter/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { createVolume, deleteVolume, listVolumes, updateVolume } from '@/entities/volume/api'
import type { CreateVolumePayload, UpdateVolumePayload, Volume } from '@/entities/volume/types'
import ChapterTree from '@/features/chapters/ChapterTree.vue'
import ChapterEditor from '@/features/chapters/ChapterEditor.vue'
import CreateChapterDialog from '@/features/chapters/CreateChapterDialog.vue'
import EditChapterDialog from '@/features/chapters/EditChapterDialog.vue'
import CreateVolumeDialog from '@/features/volumes/CreateVolumeDialog.vue'
import EditVolumeDialog from '@/features/volumes/EditVolumeDialog.vue'

const route = useRoute()

const project = ref<Project | null>(null)
const volumes = ref<Volume[]>([])
const chapters = ref<Chapter[]>([])
const selectedChapter = ref<Chapter | null>(null)
const editingVolume = ref<Volume | null>(null)
const editingChapter = ref<Chapter | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const isChapterLoading = ref(false)
const isEditorDirty = ref(false)
const errorMessage = ref('')
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
  isEditorDirty.value = false
  void loadProjectWorkspace()
})

async function loadProjectWorkspace() {
  if (!projectId.value) {
    errorMessage.value = 'Project id is missing.'
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
    errorMessage.value = getErrorMessage(error, 'Could not load project detail.')
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
  }, 'Could not create volume.')
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
  }, 'Could not update volume.')
}

async function handleDeleteVolume(volume: Volume) {
  const confirmed = window.confirm(`Delete volume "${volume.title}"?`)

  if (!confirmed) {
    return
  }

  await saveChange(async () => {
    await deleteVolume(volume.id)
    await refreshVolumesAndChapters()
  }, 'Could not delete volume.')
}

async function handleCreateChapter(payload: CreateChapterPayload) {
  if (!projectId.value) {
    return
  }

  await saveChange(async () => {
    await createChapter(projectId.value, payload)
    showCreateChapterDialog.value = false
    await refreshVolumesAndChapters()
  }, 'Could not create chapter.')
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
  }, 'Could not update chapter.')
}

async function handleDeleteChapter(chapter: Chapter) {
  const confirmed = window.confirm(`Delete chapter "${chapter.title}"?`)

  if (!confirmed) {
    return
  }

  await saveChange(async () => {
    await deleteChapter(chapter.id)
    if (selectedChapter.value?.id === chapter.id) {
      selectedChapter.value = null
    }
    await refreshVolumesAndChapters()
  }, 'Could not delete chapter.')
}

async function handleSelectChapter(chapter: Chapter) {
  if (chapter.id === selectedChapter.value?.id) {
    return
  }

  if (isEditorDirty.value) {
    const confirmed = window.confirm('You have unsaved changes. Discard them and open another chapter?')

    if (!confirmed) {
      return
    }
  }

  isChapterLoading.value = true
  errorMessage.value = ''

  try {
    selectedChapter.value = await getChapter(chapter.id)
    isEditorDirty.value = false
  } catch (error) {
    errorMessage.value = getErrorMessage(error, 'Could not load chapter.')
  } finally {
    isChapterLoading.value = false
  }
}

async function handleChapterSaved(chapter: Chapter) {
  try {
    selectedChapter.value = await getChapter(chapter.id)
    await refreshVolumesAndChapters()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, 'Chapter saved, but refresh failed.')
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
  if (error instanceof Error) {
    return error.message
  }

  return fallback
}
</script>

<template>
  <main class="project-detail-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" to="/projects">Back to Projects</RouterLink>
        <p class="eyebrow">Project Detail</p>
        <h1>{{ project?.title || 'Loading project...' }}</h1>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="isSaving" @click="showCreateVolumeDialog = true">
          Create Volume
        </button>
        <button class="primary-button" type="button" :disabled="isSaving" @click="showCreateChapterDialog = true">
          Create Chapter
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="isLoading" class="state-message">Loading project workspace...</section>

    <section v-else class="workspace-layout">
      <aside class="sidebar">
        <ChapterTree
          :volumes="sortedVolumes"
          :chapters="sortedChapters"
          :selected-chapter-id="selectedChapter?.id ?? null"
          @select-chapter="handleSelectChapter"
          @edit-volume="editingVolume = $event"
          @delete-volume="handleDeleteVolume"
          @edit-chapter="editingChapter = $event"
          @delete-chapter="handleDeleteChapter"
        />
      </aside>

      <section class="detail-panel">
        <article v-if="selectedChapter" class="chapter-preview">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Selected Chapter</p>
              <h2>{{ selectedChapter.title }}</h2>
            </div>
            <span class="version">v{{ selectedChapter.version }}</span>
          </header>

          <dl class="metadata-grid">
            <div>
              <dt>Status</dt>
              <dd>{{ selectedChapter.status }}</dd>
            </div>
            <div>
              <dt>Word Count</dt>
              <dd>{{ selectedChapter.word_count }}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{{ formatDate(selectedChapter.updated_at) }}</dd>
            </div>
          </dl>

          <div v-if="isChapterLoading" class="chapter-loading">Loading chapter...</div>

          <ChapterEditor
            v-else
            :chapter="selectedChapter"
            @dirty-change="isEditorDirty = $event"
            @saved="handleChapterSaved"
          />
        </article>

        <article v-else class="project-summary">
          <header class="panel-header">
            <div>
              <p class="eyebrow">Project Summary</p>
              <h2>{{ project?.title || 'Project' }}</h2>
            </div>
            <span v-if="project" class="version">v{{ project.version }}</span>
          </header>

          <dl v-if="project" class="metadata-grid">
            <div>
              <dt>Genre</dt>
              <dd>{{ project.genre || 'No genre set' }}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{{ formatDate(project.updated_at) }}</dd>
            </div>
            <div>
              <dt>Volumes</dt>
              <dd>{{ volumes.length }}</dd>
            </div>
            <div>
              <dt>Chapters</dt>
              <dd>{{ chapters.length }}</dd>
            </div>
          </dl>

          <p class="summary-text">{{ project?.summary || 'No summary yet.' }}</p>
        </article>
      </section>
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
  max-width: 1280px;
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

.error-banner,
.state-message,
.workspace-layout {
  max-width: 1280px;
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
  grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.sidebar,
.detail-panel {
  min-width: 0;
}

.detail-panel > article {
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
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
    grid-template-columns: 1fr;
  }
}
</style>

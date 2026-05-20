<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import {
  createOutline,
  deleteOutline,
  getOutline,
  listProjectOutlines,
  updateOutline,
} from '@/entities/outline/api'
import type {
  OutlineItem,
  OutlineItemCreatePayload,
  OutlineItemUpdatePayload,
} from '@/entities/outline/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { listVolumes } from '@/entities/volume/api'
import type { Volume } from '@/entities/volume/types'
import CreateOutlineDialog from '@/features/outlines/CreateOutlineDialog.vue'
import OutlineEditor from '@/features/outlines/OutlineEditor.vue'
import OutlineTree from '@/features/outlines/OutlineTree.vue'

const route = useRoute()

const project = ref<Project | null>(null)
const outlines = ref<OutlineItem[]>([])
const volumes = ref<Volume[]>([])
const chapters = ref<Chapter[]>([])
const selectedOutline = ref<OutlineItem | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const showCreateDialog = ref(false)

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
  void loadWorkspace()
})

watch(projectId, () => {
  selectedOutline.value = null
  void loadWorkspace()
})

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const [projectDetail, projectOutlines, projectVolumes, projectChapters] = await Promise.all([
      getProject(projectId.value),
      listProjectOutlines(projectId.value),
      listVolumes(projectId.value),
      listChapters(projectId.value),
    ])

    project.value = projectDetail
    outlines.value = projectOutlines
    volumes.value = projectVolumes
    chapters.value = projectChapters
    syncSelectedOutline()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载大纲失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshOutlines() {
  if (!projectId.value) {
    return
  }

  outlines.value = await listProjectOutlines(projectId.value)
  syncSelectedOutline()
}

async function handleSelectOutline(outline: OutlineItem) {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedOutline.value = await getOutline(outline.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载大纲详情失败。')
  }
}

async function handleCreateOutline(payload: OutlineItemCreatePayload) {
  if (!projectId.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const created = await createOutline(projectId.value, payload)
    showCreateDialog.value = false
    selectedOutline.value = created
    await refreshOutlines()
    successMessage.value = '大纲已创建。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '新建大纲失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleSaveOutline(payload: OutlineItemUpdatePayload) {
  if (!selectedOutline.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedOutline.value = await updateOutline(selectedOutline.value.id, payload)
    await refreshOutlines()
    successMessage.value = '大纲已保存'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '保存大纲失败。')
  } finally {
    isSaving.value = false
  }
}

async function handleDeleteOutline() {
  if (!selectedOutline.value) {
    return
  }

  const confirmed = window.confirm('确认删除该大纲条目吗？子条目不会被物理删除，但可能失去清晰的层级关系。')
  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await deleteOutline(selectedOutline.value.id)
    selectedOutline.value = null
    await refreshOutlines()
    successMessage.value = '大纲已删除。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除大纲失败。')
  } finally {
    isSaving.value = false
  }
}

function syncSelectedOutline() {
  if (!selectedOutline.value) {
    return
  }

  selectedOutline.value =
    outlines.value.find((outline) => outline.id === selectedOutline.value?.id) ?? null
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="outline-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">大纲规划</p>
        <h1>大纲与细纲</h1>
        <p class="project-title">{{ project?.title || '正在加载项目……' }}</p>
      </div>
      <button class="primary-button" type="button" :disabled="isSaving" @click="showCreateDialog = true">
        新建大纲条目
      </button>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section v-if="successMessage" class="success-banner" role="status">
      {{ successMessage }}
    </section>

    <section v-if="isLoading" class="state-message">正在加载大纲……</section>

    <section v-else class="outline-layout">
      <aside class="tree-panel">
        <OutlineTree
          :items="outlines"
          :selected-outline-id="selectedOutline?.id ?? null"
          @select="handleSelectOutline"
        />
      </aside>

      <section class="editor-panel">
        <OutlineEditor
          v-if="selectedOutline"
          :outline="selectedOutline"
          :outlines="outlines"
          :volumes="sortedVolumes"
          :chapters="sortedChapters"
          :is-saving="isSaving"
          @save="handleSaveOutline"
          @delete="handleDeleteOutline"
        />

        <article v-else class="empty-detail">
          <h2>请选择一个大纲条目，或新建大纲。</h2>
          <p>可以先创建全书大纲，再逐步添加分卷大纲、章节细纲、场景和剧情节点。</p>
        </article>
      </section>
    </section>

    <CreateOutlineDialog
      v-if="showCreateDialog"
      :outlines="outlines"
      :volumes="sortedVolumes"
      :chapters="sortedChapters"
      :is-saving="isSaving"
      @close="showCreateDialog = false"
      @submit="handleCreateOutline"
    />
  </main>
</template>

<style scoped>
.outline-page {
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
.outline-layout {
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
.project-title {
  margin: 0;
  color: #64748b;
  font-weight: 800;
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 0.78rem;
}

h1 {
  margin: 0 0 8px;
  font-size: 2rem;
  line-height: 1.1;
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

.state-message {
  display: grid;
  place-items: center;
  min-height: 360px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
}

.outline-layout {
  display: grid;
  grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.tree-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.empty-detail {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  min-height: 420px;
  color: #64748b;
  text-align: center;
}

.empty-detail h2,
.empty-detail p {
  margin: 0;
}

.empty-detail h2 {
  color: #111827;
  font-size: 1.2rem;
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

@media (max-width: 860px) {
  .outline-page {
    padding: 24px 16px;
  }

  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .outline-layout {
    grid-template-columns: 1fr;
  }
}
</style>

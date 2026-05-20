<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import {
  createProject,
  deleteProject,
  listProjects,
  updateProject,
} from '@/entities/project/api'
import type { CreateProjectPayload, Project, UpdateProjectPayload } from '@/entities/project/types'
import CreateProjectDialog from '@/features/projects/CreateProjectDialog.vue'
import EditProjectDialog from '@/features/projects/EditProjectDialog.vue'

const projects = ref<Project[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showCreateDialog = ref(false)
const editingProject = ref<Project | null>(null)

const hasProjects = computed(() => projects.value.length > 0)

onMounted(() => {
  void refreshProjects()
})

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

async function handleCreate(payload: CreateProjectPayload) {
  isSaving.value = true
  errorMessage.value = ''

  try {
    await createProject(payload)
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

async function handleDelete(project: Project) {
  const confirmed = window.confirm(`确定要删除项目“${project.title}”吗？`)

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

function formatUpdatedAt(value: string): string {
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
  <main class="projects-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">掌书 Next</p>
        <h1>项目</h1>
      </div>
      <div class="header-actions">
        <RouterLink class="secondary-link" to="/imports">导入作品</RouterLink>
        <button class="primary-button" type="button" :disabled="isSaving" @click="showCreateDialog = true">
          新建项目
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section class="content-panel" aria-live="polite">
      <div v-if="isLoading" class="state-message">正在加载项目……</div>

      <div v-else-if="!hasProjects" class="empty-state">
        <h2>暂无项目</h2>
        <p>新建一个小说项目，开始整理你的创作资料。</p>
      </div>

      <div v-else class="project-grid">
        <article v-for="project in projects" :key="project.id" class="project-card">
          <header class="project-card-header">
            <div>
              <h2>{{ project.title }}</h2>
              <p class="genre">{{ project.genre || '未设置类型' }}</p>
            </div>
            <span class="version">v{{ project.version }}</span>
          </header>

          <p class="summary">{{ project.summary || '暂无项目简介。' }}</p>

          <footer class="project-card-footer">
            <span>更新于 {{ formatUpdatedAt(project.updated_at) }}</span>
            <div class="card-actions">
              <RouterLink class="open-link" :to="`/projects/${project.id}`">打开</RouterLink>
              <button class="secondary-button" type="button" :disabled="isSaving" @click="editingProject = project">
                编辑
              </button>
              <button class="danger-button" type="button" :disabled="isSaving" @click="handleDelete(project)">
                删除
              </button>
            </div>
          </footer>
        </article>
      </div>
    </section>

    <CreateProjectDialog
      v-if="showCreateDialog"
      @close="showCreateDialog = false"
      @submit="handleCreate"
    />

    <EditProjectDialog
      v-if="editingProject"
      :project="editingProject"
      @close="editingProject = null"
      @submit="handleEdit"
    />
  </main>
</template>

<style scoped>
.projects-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 40px;
  background: #f6f8fb;
  color: #111827;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  max-width: 1120px;
  margin: 0 auto 24px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.1;
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
  margin-bottom: 16px;
  border: 1px solid #f4b4ad;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff1f0;
  color: #9f1c12;
  font-weight: 700;
}

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 320px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
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
  color: #1f2937;
  font-size: 1.25rem;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.project-card {
  display: grid;
  gap: 18px;
  min-height: 220px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.project-card-header,
.project-card-footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.project-card h2 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 1.15rem;
  line-height: 1.25;
}

.genre,
.summary,
.project-card-footer {
  color: #64748b;
}

.genre,
.summary {
  margin: 0;
}

.summary {
  line-height: 1.6;
  white-space: pre-wrap;
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

.project-card-footer {
  align-items: center;
  margin-top: auto;
  font-size: 0.86rem;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.open-link {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  box-sizing: border-box;
  border-radius: 6px;
  padding: 0 14px;
  background: #2563eb;
  color: #ffffff;
  font-weight: 800;
  text-decoration: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
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

@media (max-width: 720px) {
  .projects-page {
    padding: 24px 16px;
  }

  .page-header,
  .header-actions,
  .project-card-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button,
  .secondary-link {
    justify-content: center;
    width: 100%;
  }
}
</style>

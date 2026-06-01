<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { importRemoteCloudProject, listRemoteCloudProjects } from '@/entities/cloud/api'
import type { CloudRemoteProject } from '@/entities/cloud/types'
import { ApiError } from '@/shared/api/client'

const emit = defineEmits<{
  close: []
  imported: []
}>()

const router = useRouter()

const projects = ref<CloudRemoteProject[]>([])
const isLoading = ref(false)
const isImporting = ref(false)
const activeProjectId = ref<string | null>(null)
const errorMessage = ref('')
const suggestionMessage = ref('')

onMounted(() => {
  void loadProjects()
})

async function loadProjects() {
  isLoading.value = true
  errorMessage.value = ''
  suggestionMessage.value = ''
  try {
    projects.value = await listRemoteCloudProjects()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载云端项目失败。'
    if (error instanceof ApiError && error.suggestion) {
      suggestionMessage.value = error.suggestion
    }
  } finally {
    isLoading.value = false
  }
}

function handleOpenLocal(project: CloudRemoteProject) {
  // Linked locally — open existing project directly, no API call
  if (project.local_project_id) {
    emit('close')
    router.push(`/projects/${project.local_project_id}`)
  }
}

async function handleRestore(project: CloudRemoteProject) {
  isImporting.value = true
  activeProjectId.value = project.id
  errorMessage.value = ''
  suggestionMessage.value = ''

  try {
    const result = await importRemoteCloudProject(project.id)
    // Safety net: if backend returns already_exists, still navigate
    if (result.mode === 'already_exists') {
      emit('close')
      router.push(`/projects/${result.local_project_id}`)
      return
    }
    emit('imported')
    emit('close')
    router.push(`/projects/${result.local_project_id}`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '恢复失败。'
    if (error instanceof ApiError && error.suggestion) {
      suggestionMessage.value = error.suggestion
    }
  } finally {
    isImporting.value = false
    activeProjectId.value = null
  }
}
</script>

<template>
  <div class="dialog-overlay" @click.self="emit('close')">
    <div class="dialog-panel">
      <header class="dialog-header">
        <h2>从云端恢复项目</h2>
        <button class="close-button" type="button" @click="emit('close')">×</button>
      </header>

      <section v-if="errorMessage" class="error-banner" role="alert">
        <p class="error-text">{{ errorMessage }}</p>
        <p v-if="suggestionMessage" class="suggestion-text">{{ suggestionMessage }}</p>
      </section>

      <section class="dialog-body">
        <div v-if="isLoading" class="state-message">正在加载云端项目……</div>

        <div v-else-if="projects.length === 0" class="state-message">
          云端没有可恢复的项目。
        </div>

        <ul v-else class="project-list">
          <li v-for="project in projects" :key="project.id" class="project-item">
            <div class="project-info">
              <strong>{{ project.title }}</strong>
              <span v-if="project.updated_at" class="project-date">
                更新于 {{ project.updated_at.slice(0, 10) }}
              </span>
              <span v-if="project.linked_locally" class="project-linked-badge">
                本机已有
              </span>
            </div>
            <!-- Linked locally: open existing project -->
            <button
              v-if="project.linked_locally && project.local_project_id"
              class="secondary-button"
              type="button"
              @click="handleOpenLocal(project)"
            >
              打开本机项目
            </button>
            <!-- Not linked: restore as new project -->
            <button
              v-else
              class="primary-button"
              type="button"
              :disabled="isImporting"
              @click="handleRestore(project)"
            >
              {{ isImporting && activeProjectId === project.id ? '恢复中……' : '恢复为新项目' }}
            </button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.4);
}

.dialog-panel {
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.18));
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--zs-color-border);
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--zs-color-text-muted);
  padding: 0 4px;
  line-height: 1;
}

.dialog-body {
  overflow-y: auto;
  padding: 16px 20px;
}

.error-banner {
  margin: 0 20px;
  padding: 10px 14px;
  border: 1px solid var(--zs-color-danger);
  border-radius: 8px;
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-size: 0.86rem;
}

.error-text {
  margin: 0;
  font-weight: 700;
}

.suggestion-text {
  margin: 6px 0 0;
  color: var(--zs-color-text-muted);
  font-weight: 400;
  font-size: 0.82rem;
  line-height: 1.5;
}

.state-message {
  text-align: center;
  color: var(--zs-color-text-muted);
  padding: 40px 0;
}

.project-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface-soft, #fafafa);
}

.project-info {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.project-info strong {
  font-size: 0.92rem;
}

.project-date {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.project-linked-badge {
  display: inline-block;
  margin-top: 2px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #16a34a);
  font-size: 0.72rem;
  font-weight: 600;
  width: fit-content;
}

.primary-button {
  flex-shrink: 0;
  min-height: 34px;
  border: none;
  border-radius: 6px;
  padding: 0 14px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font: inherit;
  font-weight: 800;
  font-size: 0.84rem;
  cursor: pointer;
}

.primary-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.secondary-button {
  flex-shrink: 0;
  min-height: 34px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
}

.secondary-button:hover {
  background: var(--zs-color-surface-soft, #f5f5f5);
}
</style>

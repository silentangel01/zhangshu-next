<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { getProjectCoverUrl } from '@/entities/project/api'
import type { Project, ProjectStatus, UpdateProjectPayload } from '@/entities/project/types'
import ProjectCoverUploader from '@/features/projects/ProjectCoverUploader.vue'
import ProjectTagInput from '@/features/projects/ProjectTagInput.vue'

const props = defineProps<{
  project: Project
  tagSuggestions: string[]
  defaultCoverUrl: string
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: UpdateProjectPayload]
  'upload-cover': [file: File]
  'delete-cover': []
}>()

const form = reactive({
  title: props.project.title,
  author: props.project.author ?? '',
  genre: props.project.genre ?? '',
  summary: props.project.summary ?? '',
  tags: [...props.project.tags],
  status: props.project.status ?? ('planning' as ProjectStatus),
  targetWordCount: props.project.target_word_count?.toString() ?? '',
})

const coverFile = ref<File | null>(null)
const titleError = ref('')

const STATUS_OPTIONS: { value: ProjectStatus; label: string }[] = [
  { value: 'planning', label: '筹备中' },
  { value: 'writing', label: '连载中' },
  { value: 'paused', label: '暂停' },
  { value: 'completed', label: '已完结' },
  { value: 'archived', label: '已归档' },
]

watch(
  () => props.project,
  (project) => {
    form.title = project.title
    form.author = project.author ?? ''
    form.genre = project.genre ?? ''
    form.summary = project.summary ?? ''
    form.tags = [...project.tags]
    form.status = project.status ?? 'planning'
    form.targetWordCount = project.target_word_count?.toString() ?? ''
    coverFile.value = null
    titleError.value = ''
  },
)

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function parseTargetWordCount(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  const parsed = Number.parseInt(trimmed, 10)
  if (Number.isNaN(parsed) || parsed < 0) {
    return null
  }
  return parsed
}

function handleCoverSelect(file: File) {
  coverFile.value = file
  emit('upload-cover', file)
}

function handleCoverClear() {
  coverFile.value = null
  emit('delete-cover')
}

function getCoverUrl(): string | null {
  if (coverFile.value) {
    return null
  }
  return props.project.cover_image_path
    ? getProjectCoverUrl(props.project.id, props.project.version)
    : null
}

function handleSubmit() {
  const title = form.title.trim()

  if (!title) {
    titleError.value = '书名不能为空。'
    return
  }

  titleError.value = ''
  emit('submit', {
    title,
    author: normalizeOptional(form.author),
    genre: normalizeOptional(form.genre),
    summary: normalizeOptional(form.summary),
    tags: form.tags,
    status: form.status,
    target_word_count: parseTargetWordCount(form.targetWordCount),
  })
}
</script>

<template>
  <div class="zs-dialog" role="presentation">
    <section class="zs-dialog-content" role="dialog" aria-modal="true" aria-labelledby="edit-project-title">
      <header class="zs-dialog-header">
        <h2 id="edit-project-title">编辑书籍</h2>
        <button class="zs-icon-button" type="button" aria-label="关闭" @click="emit('close')">x</button>
      </header>

      <form class="project-form" @submit.prevent="handleSubmit">
        <div class="form-row">
          <div class="form-main">
            <label class="zs-field">
              <span>书名</span>
              <input v-model="form.title" name="title" type="text" autocomplete="off" required />
            </label>
            <p v-if="titleError" class="field-error">{{ titleError }}</p>

            <label class="zs-field">
              <span>作者</span>
              <input v-model="form.author" name="author" type="text" autocomplete="off" />
            </label>

            <label class="zs-field">
              <span>题材 / 类型</span>
              <input v-model="form.genre" name="genre" type="text" autocomplete="off" />
            </label>

            <label class="zs-field">
              <span>简介</span>
              <textarea v-model="form.summary" name="summary" rows="4" />
            </label>
          </div>

          <div class="form-side">
            <ProjectCoverUploader
              :cover-url="getCoverUrl()"
              :default-cover-url="defaultCoverUrl"
              @select-file="handleCoverSelect"
              @clear-cover="handleCoverClear"
            />
          </div>
        </div>

        <label class="zs-field">
          <span>标签</span>
          <ProjectTagInput
            v-model="form.tags"
            :suggestions="tagSuggestions"
          />
        </label>

        <div class="form-inline-row">
          <label class="zs-field inline-field">
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </label>

          <label class="zs-field inline-field">
            <span>目标字数</span>
            <input
              v-model="form.targetWordCount"
              name="targetWordCount"
              type="number"
              min="0"
              step="1000"
              placeholder="可选"
            />
          </label>
        </div>

        <footer class="zs-dialog-footer">
          <button class="zs-button zs-button-secondary" type="button" @click="emit('close')">取消</button>
          <button class="zs-button zs-button-primary" type="submit">保存</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.25rem;
}

.project-form {
  display: grid;
  gap: 16px;
  padding: 20px 24px 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 20px;
  align-items: start;
}

.form-main {
  display: grid;
  gap: 16px;
}

.form-side {
  display: grid;
  gap: 8px;
}

.form-inline-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.field-error {
  margin: -8px 0 0;
  color: var(--zs-color-danger);
  font-size: 0.9rem;
}

@media (max-width: 560px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .form-inline-row {
    grid-template-columns: 1fr;
  }
}
</style>
